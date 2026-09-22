import Foundation

struct TodayResponse: Codable {
    let generatedAt: String?
    let overall: OverallState
    let phase: PhaseSummary
    let progress: ProgressSummary
    let notDoneToday: [ReminderItem]
    let tripwire: TripwireItem?
    let nextAction: NextAction
    let capture: CaptureContract
    let recentCapture: [RecentCaptureItem]
    let reviewLinks: ReviewLinks

    enum CodingKeys: String, CodingKey {
        case generatedAt = "generated_at"
        case overall
        case phase
        case progress
        case notDoneToday = "not_done_today"
        case tripwire
        case nextAction = "next_action"
        case capture
        case recentCapture = "recent_capture"
        case reviewLinks = "review_links"
    }
}

struct OverallState: Codable {
    let state: String?
    let tone: String?
    let phrase: String?
}

struct PhaseSummary: Codable {
    let title: String?
    let status: String?
    let dayCount: Int?
    let nextAnchor: String?
    let openDecision: String?

    enum CodingKeys: String, CodingKey {
        case title
        case status
        case dayCount = "day_count"
        case nextAnchor = "next_anchor"
        case openDecision = "open_decision"
    }
}

struct ProgressSummary: Codable {
    let primaryLabel: String?
    let primaryValue: Double?
    let primaryUnit: String?
    let targetBand: [Double]?
    let targetLabel: String?
    let rateValue: Double?
    let rateUnit: String?
    let projectedTargetDate: String?
    let goalDeltaKg: Double?
    let latestDexa: DexaSnapshot?
    let estimate: EstimateSummary?

    enum CodingKeys: String, CodingKey {
        case primaryLabel = "primary_label"
        case primaryValue = "primary_value"
        case primaryUnit = "primary_unit"
        case targetBand = "target_band"
        case targetLabel = "target_label"
        case rateValue = "rate_value"
        case rateUnit = "rate_unit"
        case projectedTargetDate = "projected_target_date"
        case goalDeltaKg = "goal_delta_kg"
        case latestDexa = "latest_dexa"
        case estimate
    }
}

struct DexaSnapshot: Codable {
    let scanDate: String?
    let provider: String?
    let weightKg: Double?
    let bodyFatPct: Double?
    let fatMassKg: Double?
    let leanBmcKg: Double?

    enum CodingKeys: String, CodingKey {
        case scanDate = "scan_date"
        case provider
        case weightKg = "weight_kg"
        case bodyFatPct = "body_fat_pct"
        case fatMassKg = "fat_mass_kg"
        case leanBmcKg = "lean_bmc_kg"
    }
}

struct EstimateSummary: Codable {
    let available: Bool?
    let bodyFatRange: String?
    let confidence: String?

    enum CodingKeys: String, CodingKey {
        case available
        case bodyFatRange = "body_fat_range"
        case confidence
    }
}

struct ReminderItem: Codable, Identifiable {
    let id: String
    let title: String
    let detail: String
    let due: String
    let state: String
}

struct TripwireItem: Codable, Identifiable {
    let id: String
    let title: String?
    let state: String?
    let severity: String?
    let rule: String?
    let evidence: String?
    let recommendedAction: String?
    let reviewDate: String?
    let resolutionCondition: String?

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case state
        case severity
        case rule
        case evidence
        case recommendedAction = "recommended_action"
        case reviewDate = "review_date"
        case resolutionCondition = "resolution_condition"
    }
}

struct NextAction: Codable {
    let title: String?
    let why: String?
    let supportingMeasurements: [String]
    let confidence: String?
    let reviewDate: String?
    let sourceTripwire: String?

    enum CodingKeys: String, CodingKey {
        case title
        case why
        case supportingMeasurements = "supporting_measurements"
        case confidence
        case reviewDate = "review_date"
        case sourceTripwire = "source_tripwire"
    }
}

struct CaptureContract: Codable {
    let primaryPrompt: String?
    let endpoint: String?
    let authRequired: Bool?
    let examples: [String]
    let quickActions: [QuickAction]
    let intents: [String]
    let writeStatus: String?

    enum CodingKeys: String, CodingKey {
        case primaryPrompt = "primary_prompt"
        case endpoint
        case authRequired = "auth_required"
        case examples
        case quickActions = "quick_actions"
        case intents
        case writeStatus = "write_status"
    }
}

struct QuickAction: Codable, Identifiable {
    let intent: String
    let label: String

    var id: String { intent }
}

struct RecentCaptureItem: Codable, Identifiable {
    let occurredAt: String
    let source: String
    let title: String
    let detail: String

    var id: String { "\(source)-\(occurredAt)-\(title)" }

    enum CodingKeys: String, CodingKey {
        case occurredAt = "occurred_at"
        case source
        case title
        case detail
    }
}

struct ReviewLinks: Codable {
    let dashboard: String?
    let overviewJson: String?
    let contextPacket: String?

    enum CodingKeys: String, CodingKey {
        case dashboard
        case overviewJson = "overview_json"
        case contextPacket = "context_packet"
    }
}

struct ContextPacketResponse: Codable {
    let format: String
    let markdown: String
}

struct CaptureRequest: Codable {
    let intent: String
    let text: String
    let occurredAt: String?
    let source: String
    let fields: [String: String]

    enum CodingKeys: String, CodingKey {
        case intent
        case text
        case occurredAt = "occurred_at"
        case source
        case fields
    }
}

struct CaptureResponse: Codable {
    let ok: Bool
    let intent: String
    let storedAs: String?
    let recordsWritten: Int
    let ids: [String]
    let needsReview: Bool
    let missingFields: [String]?
    let summary: String

    enum CodingKeys: String, CodingKey {
        case ok
        case intent
        case storedAs = "stored_as"
        case recordsWritten = "records_written"
        case ids
        case needsReview = "needs_review"
        case missingFields = "missing_fields"
        case summary
    }
}
