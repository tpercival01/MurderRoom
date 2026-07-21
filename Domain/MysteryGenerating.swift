protocol MysteryGenerating {
    func generate(from roomObjects: [RoomObject]) async throws -> MysteryCase
}
