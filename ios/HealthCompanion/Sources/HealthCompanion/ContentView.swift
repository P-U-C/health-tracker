import SwiftUI

struct ContentView: View {
    @StateObject private var store = HealthStore()

    var body: some View {
        TabView {
            TodayView(today: store.today, isLoading: store.isLoading, errorMessage: store.errorMessage) {
                Task { await store.refresh() }
            }
            .tabItem { Label("Today", systemImage: "checkmark.circle") }

            HealthProgressView(today: store.today)
                .tabItem { Label("Progress", systemImage: "chart.xyaxis.line") }

            TripwiresView(today: store.today)
                .tabItem { Label("Tripwires", systemImage: "exclamationmark.triangle") }

            CaptureView(
                today: store.today,
                isSubmitting: store.isSubmittingCapture,
                statusMessage: store.captureStatusMessage
            ) { intent, text in
                Task { await store.submitCapture(intent: intent, text: text) }
            }
            .tabItem { Label("Capture", systemImage: "mic.circle") }

            ContextView(markdown: store.contextPacket)
                .tabItem { Label("Context", systemImage: "text.quote") }
        }
        .task { await store.refresh() }
    }
}

struct TodayView: View {
    let today: TodayResponse?
    let isLoading: Bool
    let errorMessage: String?
    let refresh: () -> Void

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if let errorMessage {
                        StatusBanner(title: "Service issue", detail: errorMessage, tone: .coral)
                    }

                    HeaderCard(today: today, isLoading: isLoading, refresh: refresh)

                    if let progress = today?.progress {
                        ProgressHero(progress: progress)
                    }

                    ReminderList(items: today?.notDoneToday ?? [])

                    if let tripwire = today?.tripwire {
                        TripwireCard(tripwire: tripwire)
                    }

                    if let action = today?.nextAction {
                        NextActionCard(action: action)
                    }
                }
                .padding()
            }
            .navigationTitle("Health")
            .toolbar {
                Button(action: refresh) {
                    Image(systemName: "arrow.clockwise")
                }
                .accessibilityLabel("Refresh")
            }
        }
    }
}

struct HeaderCard: View {
    let today: TodayResponse?
    let isLoading: Bool
    let refresh: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(today?.overall.phrase ?? (isLoading ? "Loading" : "No data"))
                        .font(.system(.largeTitle, design: .rounded, weight: .bold))
                    Text(today?.phase.title ?? "Waiting for health state")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                ToneDot(tone: today?.overall.tone)
            }

            HStack(spacing: 12) {
                StatPill(label: "Day", value: "\(today?.phase.dayCount ?? 0)")
                StatPill(label: "Status", value: today?.phase.status ?? "unknown")
                if let nextAnchor = today?.phase.nextAnchor {
                    StatPill(label: "Anchor", value: nextAnchor)
                }
            }
        }
        .modifier(CardStyle())
    }
}

struct ProgressHero: View {
    let progress: ProgressSummary

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Progress")
                .font(.headline)
            HStack(alignment: .lastTextBaseline) {
                Text(format(progress.primaryValue))
                    .font(.system(size: 44, weight: .bold, design: .rounded))
                Text(progress.primaryUnit ?? "")
                    .font(.title3)
                    .foregroundStyle(.secondary)
                Spacer()
            }
            Text(progress.primaryLabel ?? "Primary metric")
                .foregroundStyle(.secondary)
            HStack(spacing: 12) {
                StatPill(label: "Target", value: progress.targetLabel ?? "not set")
                StatPill(label: "Rate", value: format(progress.rateValue, unit: progress.rateUnit))
            }
            if let estimate = progress.estimate, estimate.available == true {
                Text("Estimated body fat: \(estimate.bodyFatRange ?? "unknown")% (\(estimate.confidence ?? "unknown") confidence)")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .modifier(CardStyle())
    }
}

struct ReminderList: View {
    let items: [ReminderItem]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Not Done Today")
                .font(.headline)
            if items.isEmpty {
                Text("No open adherence items surfaced by deterministic rules.")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(items) { item in
                    HStack(alignment: .top, spacing: 10) {
                        Image(systemName: "circle")
                            .foregroundStyle(.secondary)
                            .padding(.top, 2)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(item.title)
                                .font(.subheadline.weight(.semibold))
                            Text(item.detail)
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        Text(item.due)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.vertical, 4)
                }
            }
        }
        .modifier(CardStyle())
    }
}

struct TripwireCard: View {
    let tripwire: TripwireItem

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Tripwire")
                    .font(.headline)
                Spacer()
                Text(tripwire.state ?? "unknown")
                    .font(.caption.weight(.semibold))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.coral.opacity(0.12), in: Capsule())
            }
            Text(tripwire.title ?? "Unnamed rule")
                .font(.title3.weight(.semibold))
            Text(tripwire.evidence ?? "No evidence provided")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Text("Resolution: \(tripwire.resolutionCondition ?? "not specified")")
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
        .modifier(CardStyle())
    }
}

struct NextActionCard: View {
    let action: NextAction

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Next Action")
                .font(.headline)
            Text(action.title ?? "No action surfaced")
                .font(.title3.weight(.semibold))
            Text(action.why ?? "No rationale available")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            if let review = action.reviewDate {
                Text("Review: \(review)")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .modifier(CardStyle())
    }
}

struct HealthProgressView: View {
    let today: TodayResponse?

    var body: some View {
        NavigationStack {
            List {
                Section("Body") {
                    LabeledContent("Weight", value: format(today?.progress.primaryValue, unit: today?.progress.primaryUnit))
                    LabeledContent("Target", value: today?.progress.targetLabel ?? "not set")
                    LabeledContent("Rate", value: format(today?.progress.rateValue, unit: today?.progress.rateUnit))
                    LabeledContent("Latest DEXA", value: today?.progress.latestDexa?.scanDate ?? "none")
                }
                Section("Estimate") {
                    LabeledContent("Body fat range", value: today?.progress.estimate?.bodyFatRange ?? "not available")
                    LabeledContent("Confidence", value: today?.progress.estimate?.confidence ?? "none")
                }
            }
            .navigationTitle("Progress")
        }
    }
}

struct TripwiresView: View {
    let today: TodayResponse?

    var body: some View {
        NavigationStack {
            List {
                if let tripwire = today?.tripwire {
                    Section(tripwire.title ?? "Tripwire") {
                        LabeledContent("State", value: tripwire.state ?? "unknown")
                        LabeledContent("Severity", value: tripwire.severity ?? "unknown")
                        Text(tripwire.rule ?? "No rule text")
                        Text(tripwire.evidence ?? "No evidence")
                            .foregroundStyle(.secondary)
                    }
                } else {
                    Text("No active tripwire.")
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Tripwires")
        }
    }
}

struct CaptureView: View {
    let today: TodayResponse?
    let isSubmitting: Bool
    let statusMessage: String?
    let submit: (String, String) -> Void

    @AppStorage("healthAppToken") private var appToken = ""
    @State private var note = ""
    @State private var selectedIntent = "event"

    var actions: [QuickAction] {
        let actions = today?.capture.quickActions ?? []
        return actions.isEmpty ? [QuickAction(intent: "event", label: "Event")] : actions
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text(today?.capture.primaryPrompt ?? "What happened today?")
                        .font(.title2.weight(.semibold))

                    Picker("Intent", selection: $selectedIntent) {
                        ForEach(actions) { action in
                            Text(action.label).tag(action.intent)
                        }
                    }
                    .pickerStyle(.menu)

                    TextField("Type or dictate a note", text: $note, axis: .vertical)
                        .textFieldStyle(.roundedBorder)
                        .lineLimit(4...8)

                    SecureField("Health app token", text: $appToken)
                        .textFieldStyle(.roundedBorder)
                        .textContentType(.password)

                    Button {
                        submit(selectedIntent, note)
                    } label: {
                        Label(isSubmitting ? "Logging" : "Log", systemImage: "checkmark.circle")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(note.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSubmitting)

                    if let statusMessage {
                        StatusBanner(title: "Capture", detail: statusMessage, tone: .green)
                    }

                    RecentCaptureList(items: today?.recentCapture ?? [])

                    VStack(alignment: .leading, spacing: 8) {
                        Text("Examples")
                            .font(.headline)
                        ForEach(today?.capture.examples ?? [], id: \.self) { example in
                            Button {
                                note = example
                            } label: {
                                Text(example)
                                    .font(.subheadline)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }
                            .buttonStyle(.plain)
                            .foregroundStyle(.secondary)
                        }
                    }
                    .modifier(CardStyle())
                }
                .padding()
            }
            .navigationTitle("Capture")
        }
    }
}

struct RecentCaptureList: View {
    let items: [RecentCaptureItem]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Recent")
                .font(.headline)
            if items.isEmpty {
                Text("No app captures yet.")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(items) { item in
                    VStack(alignment: .leading, spacing: 2) {
                        Text(item.title)
                            .font(.subheadline.weight(.semibold))
                        Text(item.detail)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                        Text(item.occurredAt)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.vertical, 4)
                }
            }
        }
        .modifier(CardStyle())
    }
}

struct ContextView: View {
    let markdown: String

    @AppStorage("claudeProjectURL") private var claudeProjectURL = ""
    @AppStorage("chatGPTProjectURL") private var chatGPTProjectURL = ""

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    ProjectLinksCard(claudeProjectURL: $claudeProjectURL, chatGPTProjectURL: $chatGPTProjectURL)

                    Text(markdown.isEmpty ? "Context packet unavailable." : markdown)
                        .font(.system(.body, design: .monospaced))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .modifier(CardStyle())
                }
                .padding()
            }
            .navigationTitle("Context")
            .toolbar {
                ShareLink(item: markdown) {
                    Image(systemName: "square.and.arrow.up")
                }
                .disabled(markdown.isEmpty)
            }
        }
    }
}

struct ProjectLinksCard: View {
    @Binding var claudeProjectURL: String
    @Binding var chatGPTProjectURL: String

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Project Links")
                .font(.headline)
            TextField("Claude project or chat URL", text: $claudeProjectURL)
                .textFieldStyle(.roundedBorder)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
            TextField("ChatGPT project or chat URL", text: $chatGPTProjectURL)
                .textFieldStyle(.roundedBorder)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
            HStack {
                if let url = URL(string: claudeProjectURL), !claudeProjectURL.isEmpty {
                    Link(destination: url) {
                        Label("Claude", systemImage: "arrow.up.right.square")
                    }
                    .buttonStyle(.bordered)
                }
                if let url = URL(string: chatGPTProjectURL), !chatGPTProjectURL.isEmpty {
                    Link(destination: url) {
                        Label("ChatGPT", systemImage: "arrow.up.right.square")
                    }
                    .buttonStyle(.bordered)
                }
            }
        }
        .modifier(CardStyle())
    }
}

struct StatPill: View {
    let label: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label.uppercased())
                .font(.caption2.weight(.semibold))
                .foregroundStyle(.secondary)
            Text(value)
                .font(.footnote.weight(.semibold))
                .lineLimit(1)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(Color.secondary.opacity(0.08), in: Capsule())
    }
}

struct ToneDot: View {
    let tone: String?

    var color: Color {
        switch tone {
        case "green": return .green
        case "coral": return .coral
        case "amber": return .orange
        default: return .secondary
        }
    }

    var body: some View {
        Circle()
            .fill(color)
            .frame(width: 14, height: 14)
            .padding(.top, 10)
    }
}

struct StatusBanner: View {
    let title: String
    let detail: String
    let tone: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title).font(.headline)
            Text(detail).font(.footnote)
        }
        .foregroundStyle(tone)
        .padding()
        .background(tone.opacity(0.1), in: RoundedRectangle(cornerRadius: 8))
    }
}

struct CardStyle: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding()
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 8))
    }
}

extension Color {
    static let coral = Color(red: 0.88, green: 0.28, blue: 0.23)
}

func format(_ value: Double?, unit: String? = nil) -> String {
    guard let value else { return "not available" }
    let rendered = value.formatted(.number.precision(.fractionLength(0...2)))
    if let unit, !unit.isEmpty {
        return "\(rendered) \(unit)"
    }
    return rendered
}
