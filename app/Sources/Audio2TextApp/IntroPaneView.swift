import SwiftUI

struct IntroPaneView: View {
    @ObservedObject var controller: JobController
    let text: String
    let readingStyle: ReadingStyleSettings

    var body: some View {
        SimpleMarkdownView(text: text, style: readingStyle)
    }
}
