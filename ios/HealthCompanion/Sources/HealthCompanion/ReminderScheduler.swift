import Foundation
import UserNotifications

final class ReminderScheduler {
    static let shared = ReminderScheduler()

    private init() {}

    func schedule(from today: TodayResponse) {
        let center = UNUserNotificationCenter.current()
        center.requestAuthorization(options: [.alert, .sound, .badge]) { granted, _ in
            guard granted else { return }
            center.removePendingNotificationRequests(withIdentifiers: ["health.notDone", "health.tripwire"])
            self.scheduleNotDone(today.notDoneToday, center: center)
            if let tripwire = today.tripwire {
                self.scheduleTripwire(tripwire, center: center)
            }
        }
    }

    private func scheduleNotDone(_ reminders: [ReminderItem], center: UNUserNotificationCenter) {
        guard !reminders.isEmpty else { return }
        let content = UNMutableNotificationContent()
        content.title = "Health"
        content.body = reminders.prefix(2).map(\.title).joined(separator: " | ")
        content.sound = .default

        var date = DateComponents()
        date.hour = 20
        date.minute = 30
        let trigger = UNCalendarNotificationTrigger(dateMatching: date, repeats: true)
        let request = UNNotificationRequest(identifier: "health.notDone", content: content, trigger: trigger)
        center.add(request)
    }

    private func scheduleTripwire(_ tripwire: TripwireItem, center: UNUserNotificationCenter) {
        guard tripwire.state != nil else { return }
        let content = UNMutableNotificationContent()
        content.title = "Health tripwire"
        content.body = tripwire.title ?? "Review active tripwire"
        content.sound = .default

        var date = DateComponents()
        date.hour = 9
        date.minute = 0
        let trigger = UNCalendarNotificationTrigger(dateMatching: date, repeats: true)
        let request = UNNotificationRequest(identifier: "health.tripwire", content: content, trigger: trigger)
        center.add(request)
    }
}
