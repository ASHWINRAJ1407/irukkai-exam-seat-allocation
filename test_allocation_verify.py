from datetime import date, timedelta

excluded = {date(2024, 5, 2), date(2024, 5, 4)}

# Generate available dates
available = []
d = date(2024, 5, 1)
for _ in range(15):
    if d not in excluded:
        available.append(d)
    d += timedelta(days=1)

print("Available dates:", available)
print()

# D1 needs 4 dates: should get first 4
print("D1 allocated:", available[:4])

# D2 needs 3 dates: should get next 3
print("D2 allocated:", available[4:7])  

# D3 needs 2 dates: should get next 2
print("D3 allocated:", available[7:9])
