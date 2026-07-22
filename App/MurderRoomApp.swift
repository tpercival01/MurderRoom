import SwiftUI

@main
@MainActor
struct MurderRoomApp: App {
    @StateObject private var viewModel: GameViewModel

    init() {
        let generator = AIMysteryGenerator(
            baseURL: URL(
                string: "http://10.101.148.72:8000"
            )!
        )

        _viewModel = StateObject(
            wrappedValue: GameViewModel(
                generator: generator
            )
        )
    }

    var body: some Scene {
        WindowGroup {
            GameView(viewModel: viewModel)
        }
    }
}
