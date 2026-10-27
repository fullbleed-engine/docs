using System.Globalization;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Fullbleed.PdfTemplate;

internal sealed record CertificateRecord(string Name, string Workshop, DateOnly CompletedOn, string CertificateId)
{
    private static readonly string[] Months = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    public string DateLabel => FormattableString.Invariant($"{CompletedOn.Day} {Months[CompletedOn.Month]} {CompletedOn.Year}");
}

internal static class CertificateRecords
{
    private static readonly HashSet<string> Fields = ["name", "workshop", "completed_on", "certificate_id"];

    public static IReadOnlyList<CertificateRecord> Load(string path)
    {
        using var input = JsonDocument.Parse(File.ReadAllText(path));
        if (input.RootElement.ValueKind != JsonValueKind.Array || input.RootElement.GetArrayLength() == 0)
            throw new InvalidDataException("Use a nonempty JSON array of certificate records.");
        var records = new List<CertificateRecord>();
        foreach (var item in input.RootElement.EnumerateArray())
        {
            var number = records.Count + 1;
            if (item.ValueKind != JsonValueKind.Object)
                throw new InvalidDataException($"Record {number}: use a JSON object.");
            var properties = item.EnumerateObject().ToArray();
            if (properties.Length != Fields.Count || !Fields.SetEquals(properties.Select(property => property.Name)))
                throw new InvalidDataException($"Record {number}: use exactly name, workshop, completed_on and certificate_id, without duplicate fields.");
            var name = Text(item, "name", 48, number);
            var workshop = Text(item, "workshop", 80, number);
            var id = Text(item, "certificate_id", 20, number);
            if (!Regex.IsMatch(id, "^[A-Za-z0-9._-]+$", RegexOptions.CultureInvariant))
                throw new InvalidDataException($"Record {number}: certificate_id accepts ASCII letters, digits, periods, underscores and hyphens.");
            var date = item.GetProperty("completed_on");
            if (date.ValueKind != JsonValueKind.String ||
                !Regex.IsMatch(date.GetString()!, "^[0-9]{4}-[0-9]{2}-[0-9]{2}$", RegexOptions.CultureInvariant) ||
                !DateOnly.TryParseExact(date.GetString(), "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var completed))
                throw new InvalidDataException($"Record {number}: completed_on must be a valid date using YYYY-MM-DD.");
            records.Add(new CertificateRecord(name, workshop, completed, id));
        }
        return records;
    }

    private static string Text(JsonElement item, string field, int limit, int number)
    {
        var element = item.GetProperty(field);
        if (element.ValueKind != JsonValueKind.String)
            throw new InvalidDataException($"Record {number}: {field} must be text.");
        var text = element.GetString()!.Trim().Normalize(NormalizationForm.FormC);
        var runes = text.EnumerateRunes().ToArray();
        if (runes.Length < 1 || runes.Length > limit || runes.Any(rune => !Printable(rune)))
            throw new InvalidDataException($"Record {number}: {field} must contain 1 to {limit} printable characters on one line.");
        return text;
    }

    private static bool Printable(Rune rune) => rune.Value == 0x20 || Rune.GetUnicodeCategory(rune) is not
        (UnicodeCategory.Control or UnicodeCategory.Format or UnicodeCategory.Surrogate or UnicodeCategory.PrivateUse or
         UnicodeCategory.OtherNotAssigned or UnicodeCategory.LineSeparator or UnicodeCategory.ParagraphSeparator or UnicodeCategory.SpaceSeparator);
}
