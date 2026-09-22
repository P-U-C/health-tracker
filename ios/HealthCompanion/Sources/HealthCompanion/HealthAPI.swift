import Foundation

@MainActor
final class HealthStore: ObservableObject {
    @Published var today: TodayResponse?
    @Published var contextPacket: String = ""
    @Published var isLoading = false
    @Published var isSubmittingCapture = false
    @Published var errorMessage: String?
    @Published var captureStatusMessage: String?

    private let api = HealthAPI()

    func refresh() async {
        isLoading = true
        errorMessage = nil
        do {
            async let todayResult = api.fetchToday()
            async let contextResult = api.fetchContextPacket()
            today = try await todayResult
            contextPacket = try await contextResult.markdown
            if let today {
                ReminderScheduler.shared.schedule(from: today)
            }
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func submitCapture(intent: String, text: String) async {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        let token = UserDefaults.standard.string(forKey: "healthAppToken") ?? ""
        isSubmittingCapture = true
        captureStatusMessage = nil
        do {
            let request = CaptureRequest(intent: intent, text: trimmed, occurredAt: nil, source: "ios", fields: [:])
            let result = try await api.submitCapture(request, token: token)
            captureStatusMessage = result.summary
            await refresh()
        } catch {
            captureStatusMessage = error.localizedDescription
        }
        isSubmittingCapture = false
    }
}

struct HealthAPI {
    var baseURL = URL(string: "https://health.permanentupperclass.com")!

    func fetchToday() async throws -> TodayResponse {
        try await get(path: "/api/mobile/today", as: TodayResponse.self)
    }

    func fetchContextPacket() async throws -> ContextPacketResponse {
        try await get(path: "/api/mobile/context", as: ContextPacketResponse.self)
    }

    func submitCapture(_ capture: CaptureRequest, token: String) async throws -> CaptureResponse {
        guard !token.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            throw APIError.missingToken
        }
        return try await post(path: "/api/mobile/capture", body: capture, token: token, as: CaptureResponse.self)
    }

    private func get<T: Decodable>(path: String, as type: T.Type) async throws -> T {
        let url = baseURL.appending(path: path)
        let (data, response) = try await URLSession.shared.data(from: url)
        try validate(response)
        let decoder = JSONDecoder()
        return try decoder.decode(type, from: data)
    }

    private func post<Body: Encodable, Response: Decodable>(path: String, body: Body, token: String, as type: Response.Type) async throws -> Response {
        let url = baseURL.appending(path: path)
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.httpBody = try JSONEncoder().encode(body)
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response)
        return try JSONDecoder().decode(type, from: data)
    }

    private func validate(_ response: URLResponse) throws {
        guard let http = response as? HTTPURLResponse else {
            throw APIError.badStatus(nil)
        }
        guard 200..<300 ~= http.statusCode else {
            throw APIError.badStatus(http.statusCode)
        }
    }
}

enum APIError: LocalizedError {
    case badStatus(Int?)
    case missingToken

    var errorDescription: String? {
        switch self {
        case .badStatus(let status):
            if let status {
                return "The health service returned HTTP \(status)."
            }
            return "The health service returned an unexpected response."
        case .missingToken:
            return "Add the health app token before logging capture."
        }
    }
}
