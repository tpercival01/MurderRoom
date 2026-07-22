import SwiftUI

struct ContentView: View {
    @ObservedObject var viewModel: GameViewModel

    var body: some View {
        GameView(viewModel: viewModel)
    }
}

#Preview {
    ContentView(
        viewModel: GameViewModel()
    )
}
