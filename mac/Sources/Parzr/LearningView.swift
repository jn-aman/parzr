import SwiftUI

/// The private weekly summary in Settings, Learning: fixes applied, by kind, and the most common slips. Built from `WritingStats`, which never leaves this Mac.
struct WeeklySummaryView: View {
    let summary: WeeklySummary
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .firstTextBaseline, spacing: 10) {
                Text("\(summary.fixes)").font(.system(size: 30, weight: .semibold)).monospacedDigit().tracking(-1)
                Text(summary.fixes == 1 ? "fix in the last 7 days" : "fixes in the last 7 days").font(.system(size: 12)).foregroundStyle(Color.textSecondary)
                Spacer(minLength: 8)
                if let trend = summary.trend { Text(trend).font(.system(size: 11)).foregroundStyle(Color.mintAccent) }
            }
            VStack(alignment: .leading, spacing: 7) {
                let top = max(1, summary.categories.map(\.count).max() ?? 1)
                ForEach(summary.categories) { item in
                    HStack(spacing: 10) {
                        Text(item.name).font(.system(size: 11)).frame(width: 96, alignment: .leading)
                        GeometryReader { geometry in
                            RoundedRectangle(cornerRadius: 2).fill(Color.mintAccent.opacity(0.75))
                                .frame(width: max(4, geometry.size.width * CGFloat(item.count) / CGFloat(top)), height: 6)
                                .frame(maxHeight: .infinity, alignment: .center)
                        }.frame(height: 12)
                        Text("\(item.count)").font(.system(size: 11)).monospacedDigit().foregroundStyle(Color.textSecondary).frame(width: 34, alignment: .trailing)
                    }.accessibilityElement(children: .ignore).accessibilityLabel("\(item.name): \(item.count)")
                }
            }
            if !summary.slips.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("MOST COMMON SLIPS").font(.system(size: 9, weight: .semibold)).tracking(1.2).foregroundStyle(Color.textSecondary)
                    ForEach(summary.slips) { slip in
                        HStack { Text(slip.name).font(.system(size: 12)); Spacer(); Text("×\(slip.count)").font(.system(size: 11)).monospacedDigit().foregroundStyle(Color.textSecondary) }
                            .accessibilityElement(children: .ignore).accessibilityLabel("\(slip.name), \(slip.count) times")
                    }
                }
            }
            Text(footnote).font(.system(size: 10)).foregroundStyle(Color.textSecondary.opacity(0.85))
        }
    }
    private var footnote: String {
        var parts = ["\(summary.activeDays) \(summary.activeDays == 1 ? "day" : "days") with fixes"]
        if let day = summary.busiestDayName, summary.activeDays > 1 { parts.append("most on \(day)") }
        if summary.ignored > 0 { parts.append("\(summary.ignored) ignored") }
        return parts.joined(separator: " · ") + ". Counted on this Mac only."
    }
}
