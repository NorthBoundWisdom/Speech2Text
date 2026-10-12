// Audio2Text-iOS shared source

import SwiftUI

struct LibraryWorkspaceShell<SourceColumn: View, ListColumn: View, DetailColumn: View>: View {
    var showsSourceColumn = true
    var sourceColumnWidth: CGFloat
    var listColumnWidth: CGFloat
    var sourceColumnMinimumWidth: CGFloat = 180
    var listColumnMinimumWidth: CGFloat = 240

    @ViewBuilder let sourceColumn: () -> SourceColumn
    @ViewBuilder let listColumn: () -> ListColumn
    @ViewBuilder let detailColumn: () -> DetailColumn

    var body: some View {
        GeometryReader { geometry in
            let sourceWidth = showsSourceColumn ? max(sourceColumnMinimumWidth, sourceColumnWidth) : 0
            let listWidth = max(listColumnMinimumWidth, listColumnWidth)
            let dividerWidth: CGFloat = showsSourceColumn ? 2 : 1
            let detailWidth = max(0, geometry.size.width - sourceWidth - listWidth - dividerWidth)

            HStack(spacing: 0) {
                if showsSourceColumn {
                    sourceColumn()
                        .frame(width: sourceWidth, height: geometry.size.height, alignment: .topLeading)
                        .clipped()

                    LibraryWorkspaceColumnDivider()
                }

                listColumn()
                    .frame(width: listWidth, height: geometry.size.height, alignment: .topLeading)
                    .clipped()

                LibraryWorkspaceColumnDivider()

                detailColumn()
                    .frame(width: detailWidth, height: geometry.size.height, alignment: .topLeading)
                    .clipped()
            }
            .frame(width: geometry.size.width, height: geometry.size.height, alignment: .topLeading)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct LibraryWorkspaceDetailHeader<Controls: View>: View {
    @ViewBuilder let controls: () -> Controls

    var body: some View {
        controls()
            .frame(minWidth: 0, maxWidth: 520)
            .frame(maxWidth: .infinity)
            .padding(.horizontal, 12)
            .frame(height: 42)
    }
}

struct LibraryWorkspaceColumnDivider: View {
    var body: some View {
        Rectangle()
            .fill(Color.secondary.opacity(0.18))
            .frame(width: 1)
            .ignoresSafeArea(.container, edges: .vertical)
    }
}
