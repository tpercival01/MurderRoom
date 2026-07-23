import SwiftUI

@main
@MainActor
struct MurderRoomApp: App {
    @StateObject private var viewModel: GameViewModel

    init() {
        let aiGenerator = AIMysteryGenerator(
            baseURL: URL(
                string: "https://api.murderroom.thomaspercival.dev"
            )!
        )

        let generator = PersistentMysteryGenerator(
            generator: aiGenerator
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
