import Foundation

#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

enum MysteryDifficulty: String, Encodable {
    case easy
    case standard
    case brutal
}

enum AIMysteryGeneratorError: Error, LocalizedError {
    case invalidRoomObjects
    case invalidHTTPResponse
    case serverRejectedRequest(
        statusCode: Int,
        detail: String
    )
    case decodingFailed(Error)
    case invalidMystery([MysteryValidationIssue])

    var errorDescription: String? {
        switch self {
        case .invalidRoomObjects:
            return """
            Exactly four distinct confirmed room objects \
            are required.
            """

        case .invalidHTTPResponse:
            return """
            The mystery server returned an invalid response.
            """

        case let .serverRejectedRequest(
            statusCode,
            detail
        ):
            return """
            Mystery generation failed with HTTP \
            \(statusCode): \(detail)
            """

        case let .decodingFailed(error):
            return """
            The generated mystery could not be decoded: \
            \(error.localizedDescription)
            """

        case let .invalidMystery(issues):
            let issueList = issues
                .map(\.rawValue)
                .joined(separator: ", ")

            return """
            The generated mystery failed local validation: \
            \(issueList)
            """
        }
    }
}

/// Performs one complete request to the backend.
///
/// A 502 means the backend exhausted its bounded retries for that
/// generated case. It is deliberately allowed to throw so the
/// persistent wrapper can start a completely fresh case.
struct AIMysteryGenerator: MysteryGenerating {
    let baseURL: URL
    let difficulty: MysteryDifficulty
    let session: URLSession

    init(
        baseURL: URL,
        difficulty: MysteryDifficulty = .standard,
        session: URLSession = .shared
    ) {
        self.baseURL = baseURL
        self.difficulty = difficulty
        self.session = session
    }

    func generate(
        from roomObjects: [RoomObject]
    ) async throws -> MysteryCase {
        let confirmedObjects = roomObjects.filter(
            \.isConfirmed
        )

        let distinctNames = Set(
            confirmedObjects.map {
                $0.name
                    .trimmingCharacters(
                        in: .whitespacesAndNewlines
                    )
                    .lowercased()
            }
        )

        guard confirmedObjects.count == 4,
              distinctNames.count == 4,
              !distinctNames.contains("")
        else {
            throw AIMysteryGeneratorError
                .invalidRoomObjects
        }

        let endpoint = baseURL.appendingPathComponent(
            "generate-case"
        )

        var request = URLRequest(url: endpoint)

        request.httpMethod = "POST"
        request.setValue(
            "application/json",
            forHTTPHeaderField: "Content-Type"
        )

        // One full phased generation can take longer than a normal
        // API request, especially when the backend rejects drafts.
        request.timeoutInterval = 180

        let payload = GenerateCaseRequest(
            roomObjects: confirmedObjects.map(\.name),
            difficulty: difficulty
        )

        request.httpBody = try JSONEncoder().encode(
            payload
        )

        let data: Data
        let response: URLResponse

        (data, response) = try await session.data(
            for: request
        )

        guard let httpResponse =
            response as? HTTPURLResponse
        else {
            throw AIMysteryGeneratorError
                .invalidHTTPResponse
        }

        guard 200..<300 ~= httpResponse.statusCode else {
            throw AIMysteryGeneratorError
                .serverRejectedRequest(
                    statusCode: httpResponse.statusCode,
                    detail: decodeServerError(from: data)
                )
        }

        let mystery: MysteryCase

        do {
            mystery = try JSONDecoder().decode(
                MysteryCase.self,
                from: data
            )
        } catch {
            throw AIMysteryGeneratorError
                .decodingFailed(error)
        }

        let validationIssues =
            MysteryValidator().validate(mystery)

        guard validationIssues.isEmpty else {
            throw AIMysteryGeneratorError
                .invalidMystery(validationIssues)
        }

        return mystery
    }

    private func decodeServerError(
        from data: Data
    ) -> String {
        if let response = try? JSONDecoder().decode(
            ServerErrorResponse.self,
            from: data
        ) {
            return response.detail
        }

        if let message = String(
            data: data,
            encoding: .utf8
        ),
           !message.isEmpty {
            return message
        }

        return "No error detail was returned."
    }
}

/// Keeps starting fresh whole-case generations until one succeeds.
///
/// The backend should keep its own retries bounded. This wrapper handles
/// the higher-level policy: a failed suspect cast or evidence board means
/// abandon that whole draft, pause briefly, then start a new case.
///
/// It stops only when the surrounding Swift task is cancelled or the
/// room-object input is invalid.
struct PersistentMysteryGenerator<
    Generator: MysteryGenerating
>: MysteryGenerating {
    let generator: Generator
    let maximumDelaySeconds: Double

    init(
        generator: Generator,
        maximumDelaySeconds: Double = 12
    ) {
        self.generator = generator
        self.maximumDelaySeconds =
            maximumDelaySeconds
    }

    func generate(
        from roomObjects: [RoomObject]
    ) async throws -> MysteryCase {
        var failedWholeCaseAttempts = 0

        while true {
            try Task.checkCancellation()

            do {
                return try await generator.generate(
                    from: roomObjects
                )
            } catch is CancellationError {
                throw CancellationError()
            } catch let error as AIMysteryGeneratorError {
                if case .invalidRoomObjects = error {
                    throw error
                }

                failedWholeCaseAttempts += 1

                try await waitBeforeRetry(
                    failedAttemptCount:
                        failedWholeCaseAttempts
                )
            } catch let error as URLError
                where error.code == .cancelled {
                throw CancellationError()
            } catch {
                failedWholeCaseAttempts += 1

                try await waitBeforeRetry(
                    failedAttemptCount:
                        failedWholeCaseAttempts
                )
            }
        }
    }

    private func waitBeforeRetry(
        failedAttemptCount: Int
    ) async throws {
        let exponent = min(
            max(failedAttemptCount - 1, 0),
            4
        )

        let baseDelay = min(
            pow(2, Double(exponent)),
            maximumDelaySeconds
        )

        let jitter = Double.random(
            in: 0.85...1.15
        )

        let delay = min(
            baseDelay * jitter,
            maximumDelaySeconds
        )

        let nanoseconds = UInt64(
            delay * 1_000_000_000
        )

        try await Task.sleep(
            nanoseconds: nanoseconds
        )
    }
}

private struct GenerateCaseRequest: Encodable {
    let roomObjects: [String]
    let difficulty: MysteryDifficulty

    enum CodingKeys: String, CodingKey {
        case roomObjects = "room_objects"
        case difficulty
    }
}

private struct ServerErrorResponse: Decodable {
    let detail: String
}

/// Retained for previews or a future explicit offline mode.
///
/// Do not wrap PersistentMysteryGenerator in this during the current
/// integration test, because a fallback would hide backend defects.
struct FallbackMysteryGenerator<
    Primary: MysteryGenerating,
    Fallback: MysteryGenerating
>: MysteryGenerating {
    let primary: Primary
    let fallback: Fallback

    func generate(
        from roomObjects: [RoomObject]
    ) async throws -> MysteryCase {
        do {
            return try await primary.generate(
                from: roomObjects
            )
        } catch {
            return try await fallback.generate(
                from: roomObjects
            )
        }
    }
}
