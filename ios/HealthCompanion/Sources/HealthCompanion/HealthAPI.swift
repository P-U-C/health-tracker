import Foundation

@MainActor
final class HealthStore: ObservableObject {
    @Published var today: TodayResponse?
    @Published var contextPacket: String = ""
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let api = HealthAPI()

    func refresh() async {
        isLoading = true
        errorMessage = nil
        do {
            async let todayResult = api.fetchToday()
            async let contextResult = api.fetchContextPacket()
            today = try await todayResult
            contextPacket = try await contextResult.markdown
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
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

    private func get<T: Decodable>(path: String, as type: T.Type) async throws -> T {
        let url = baseURL.appending(path: path)
        let (data, response) = try await URLSession.shared.data(from: url)
        guard let http = response as? HTTPURLResponse, 200..<300 ~= http.statusCode else {
            throw APIError.badStatus
        }
        let decoder = JSONDecoder()
        return try decoder.decode(type, from: data)
    }
}

enum APIError: LocalizedError {
    case badStatus

    var errorDescription: String? {
        switch self {
        case .badStatus:
            return "The health service returned an unexpected response."
        }
    }
}
