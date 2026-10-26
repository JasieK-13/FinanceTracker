from pathlib import Path

p = Path('index.html')
s = p.read_text()

if 'HOUSEHOLD_LEDGER_START = "2026-09-28"' in s:
    print('baseline already patched')
    raise SystemExit(0)

# Establish the explicit household ledger start date.
anchor = '  function slugify(s) { return String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, ""); }\n'
insert = anchor + '''  // Household ledger starts with Partner SFE on 28 Sep 2026. Nothing before this date is household history.\n  const HOUSEHOLD_LEDGER_START = "2026-09-28";\n  function isHouseholdLedgerTransaction(tx) {\n    return tx && /^(income|expense)$/.test(String(tx.type || "")) && String(tx.date || "") >= HOUSEHOLD_LEDGER_START;\n  }\n'''
if anchor not in s:
    raise SystemExit('ledger start anchor missing')
s = s.replace(anchor, insert, 1)

# Cash Now must ignore anything before 28 Sep 2026 and transfers must never affect household cash.
start = s.find('  function computeBaseTotals() {')
end = s.find('  function computeTotals() {', start)
if start < 0 or end < 0:
    raise SystemExit('computeBaseTotals anchors missing')
old_func = s[start:end]
old_loop = '''    data.transactions.forEach(t => {\n      const amt = Number(t.amount) || 0;\n      if (t.type === "income") {\n        income += amt;\n        if (t.reserved) pots[t.reserved] = (pots[t.reserved] || 0) + amt;\n        else if (monthKey(t.date) === viewMk) viewIncome += amt;\n      } else if (t.type === "expense") {\n        expense += amt;\n        if (monthKey(t.date) === viewMk) {\n          if (t.essential) viewEssential += amt; else viewNonEssential += amt;\n          catSpend[t.category] = (catSpend[t.category] || 0) + amt;\n          const key = t.category + "|" + (t.subcategory || "").trim().toLowerCase();\n          subcatSpend[key] = (subcatSpend[key] || 0) + amt;\n        }\n      } else if (t.type === "transfer") {\n        transfer += amt;\n        const pot = t.pot || "Other";\n        pots[pot] = (pots[pot] || 0) + amt;\n      }\n    });'''
new_loop = '''    data.transactions.forEach(t => {\n      const amt = Number(t.amount) || 0;\n      if (t.type === "transfer") {\n        // Internal pot moves are not household cash movements. Keep post-baseline\n        // allocations for the Pots view, but never include them in Cash Now.\n        if (String(t.date || "") >= HOUSEHOLD_LEDGER_START) {\n          transfer += amt;\n          const pot = t.pot || "Other";\n          pots[pot] = (pots[pot] || 0) + amt;\n        }\n        return;\n      }\n      if (!isHouseholdLedgerTransaction(t)) return;\n      if (t.type === "income") {\n        income += amt;\n        if (t.reserved) pots[t.reserved] = (pots[t.reserved] || 0) + amt;\n        else if (monthKey(t.date) === viewMk) viewIncome += amt;\n      } else if (t.type === "expense") {\n        expense += amt;\n        if (monthKey(t.date) === viewMk) {\n          if (t.essential) viewEssential += amt; else viewNonEssential += amt;\n          catSpend[t.category] = (catSpend[t.category] || 0) + amt;\n          const key = t.category + "|" + (t.subcategory || "").trim().toLowerCase();\n          subcatSpend[key] = (subcatSpend[key] || 0) + amt;\n        }\n      }\n    });'''
if old_loop not in old_func:
    raise SystemExit('transaction loop anchor missing')
s = s[:start] + old_func.replace(old_loop, new_loop, 1) + s[end:]

# Forecast starting cash must use exactly the same baseline.
old = '''    const startingCash = (Number(data.config.startingBalance) || 0) + data.transactions.reduce((s, tx) => {\n      if (tx.type === "income") return s + (Number(tx.amount) || 0);\n      if (tx.type === "expense") return s - (Number(tx.amount) || 0);\n      return s;\n    }, 0);'''
new = '''    const startingCash = (Number(data.config.startingBalance) || 0) + data.transactions.reduce((s, tx) => {\n      if (!isHouseholdLedgerTransaction(tx)) return s;\n      if (tx.type === "income") return s + (Number(tx.amount) || 0);\n      if (tx.type === "expense") return s - (Number(tx.amount) || 0);\n      return s;\n    }, 0);'''
if old not in s:
    raise SystemExit('forecast starting cash anchor missing')
s = s.replace(old, new, 1)

# Budget forecast must use the same baseline.
old = '      if (tx.type !== "expense" || monthKey(tx.date) !== mk) return false;'
new = '      if (!isHouseholdLedgerTransaction(tx) || tx.type !== "expense" || monthKey(tx.date) !== mk) return false;'
if old not in s:
    raise SystemExit('budget forecast anchor missing')
s = s.replace(old, new, 1)

# Spend-rate statistics must use the same baseline.
old = '    const spent = data.transactions.filter(tx => tx.type === "expense" && !tx.reserved && tx.date >= startKey && tx.date <= endKey).reduce((s,tx)=>s+(Number(tx.amount)||0),0);'
new = '    const spent = data.transactions.filter(tx => isHouseholdLedgerTransaction(tx) && tx.type === "expense" && !tx.reserved && tx.date >= startKey && tx.date <= endKey).reduce((s,tx)=>s+(Number(tx.amount)||0),0);'
if old not in s:
    raise SystemExit('spending-rate anchor missing')
s = s.replace(old, new, 1)

p.write_text(s)
print('patched household baseline calculations')
