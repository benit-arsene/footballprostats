p = "src/components/TopScorersTable.tsx"
s = open(p).read()

# Remove Print Sheet button block
i = s.find('Print Sheet')
# find the start of the button (look back for <button)
start = s.rfind('<button', 0, i)
end = s.find('</button>', i) + len('</button>')
s = s[:start] + s[end:]

# Remove Export .CSV button block
i = s.find('Export .CSV')
start = s.rfind('<button', 0, i)
end = s.find('</button>', i) + len('</button>')
s = s[:start] + s[end:]

open(p, "w").write(s)
print("done")