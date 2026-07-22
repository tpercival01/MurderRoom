import Foundation

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
        request.timeoutInterval = 90

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
