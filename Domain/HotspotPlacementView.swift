import SwiftUI
import UIKit

struct HotspotPlacementView: View {
    let image: UIImage
    let objectNames: [String]
    let hotspots: [RoomObjectHotspot]
    let activeObjectName: String?

    let onPlace: (
        String,
        CGPoint
    ) -> Void

    var body: some View {
        VStack(
            alignment: .leading,
            spacing: 12
        ) {
            instruction

            GeometryReader { geometry in
                let imageRect = fittedImageRect(
                    imageSize: image.size,
                    containerSize: geometry.size
                )

                ZStack(alignment: .topLeading) {
                    Color.black

                    Image(uiImage: image)
                        .resizable()
                        .scaledToFit()
                        .frame(
                            width: imageRect.width,
                            height: imageRect.height
                        )
                        .position(
                            x: imageRect.midX,
                            y: imageRect.midY
                        )

                    ForEach(hotspots) { hotspot in
                        hotspotMarker(hotspot)
                            .position(
                                x: imageRect.minX
                                    + hotspot.x
                                    * imageRect.width,
                                y: imageRect.minY
                                    + hotspot.y
                                    * imageRect.height
                            )
                    }

                    if let activeObjectName {
                        Rectangle()
                            .fill(.clear)
                            .contentShape(Rectangle())
                            .frame(
                                width: imageRect.width,
                                height: imageRect.height
                            )
                            .position(
                                x: imageRect.midX,
                                y: imageRect.midY
                            )
                            .gesture(
                                DragGesture(
                                    minimumDistance: 0
                                )
                                .onEnded { value in
                                    placeHotspot(
                                        objectName:
                                            activeObjectName,
                                        location:
                                            value.location,
                                        imageRect:
                                            imageRect
                                    )
                                }
                            )
                    }
                }
                .clipShape(
                    RoundedRectangle(
                        cornerRadius: 14
                    )
                )
                .overlay {
                    RoundedRectangle(
                        cornerRadius: 14
                    )
                    .stroke(
                        .secondary.opacity(0.4),
                        lineWidth: 1
                    )
                }
            }
            .aspectRatio(
                image.size.width / image.size.height,
                contentMode: .fit
            )

            placementProgress
        }
    }

    @ViewBuilder
    private var instruction: some View {
        if let activeObjectName {
            Text(
                "Tap the **\(activeObjectName)** "
                + "in the photograph."
            )
        } else {
            Label(
                "All objects placed",
                systemImage: "checkmark.circle.fill"
            )
            .foregroundStyle(.green)
        }
    }

    private var placementProgress: some View {
        VStack(
            alignment: .leading,
            spacing: 6
        ) {
            ForEach(
                Array(objectNames.enumerated()),
                id: \.offset
            ) { index, objectName in
                let isPlaced = hotspots.contains {
                    namesMatch(
                        $0.objectName,
                        objectName
                    )
                }

                Label(
                    objectName,
                    systemImage: isPlaced
                        ? "checkmark.circle.fill"
                        : "\(index + 1).circle"
                )
                .font(.caption)
                .foregroundStyle(
                    isPlaced
                        ? .green
                        : .secondary
                )
            }
        }
    }

    private func hotspotMarker(
        _ hotspot: RoomObjectHotspot
    ) -> some View {
        VStack(spacing: 3) {
            ZStack {
                Circle()
                    .fill(.blue)
                    .frame(
                        width: 38,
                        height: 38
                    )

                Image(
                    systemName: "scope"
                )
                .font(.title3)
                .fontWeight(.bold)
                .foregroundStyle(.white)
            }

            Text(hotspot.objectName)
                .font(.caption2)
                .fontWeight(.semibold)
                .foregroundStyle(.white)
                .padding(.horizontal, 6)
                .padding(.vertical, 3)
                .background(
                    .black.opacity(0.8),
                    in: Capsule()
                )
        }
    }

    private func placeHotspot(
        objectName: String,
        location: CGPoint,
        imageRect: CGRect
    ) {
        guard
            imageRect.width > 0,
            imageRect.height > 0,
            imageRect.contains(location)
        else {
            return
        }

        let normalisedPoint = CGPoint(
            x: min(
                max(
                    (
                        location.x
                        - imageRect.minX
                    ) / imageRect.width,
                    0
                ),
                1
            ),
            y: min(
                max(
                    (
                        location.y
                        - imageRect.minY
                    ) / imageRect.height,
                    0
                ),
                1
            )
        )

        onPlace(
            objectName,
            normalisedPoint
        )
    }

    private func fittedImageRect(
        imageSize: CGSize,
        containerSize: CGSize
    ) -> CGRect {
        guard
            imageSize.width > 0,
            imageSize.height > 0,
            containerSize.width > 0,
            containerSize.height > 0
        else {
            return .zero
        }

        let scale = min(
            containerSize.width
                / imageSize.width,
            containerSize.height
                / imageSize.height
        )

        let renderedSize = CGSize(
            width: imageSize.width * scale,
            height: imageSize.height * scale
        )

        return CGRect(
            x: (
                containerSize.width
                - renderedSize.width
            ) / 2,
            y: (
                containerSize.height
                - renderedSize.height
            ) / 2,
            width: renderedSize.width,
            height: renderedSize.height
        )
    }

    private func namesMatch(
        _ first: String,
        _ second: String
    ) -> Bool {
        first.trimmingCharacters(
            in: .whitespacesAndNewlines
        )
        .caseInsensitiveCompare(
            second.trimmingCharacters(
                in: .whitespacesAndNewlines
            )
        ) == .orderedSame
    }
}
