from core.fountain_unreal import export_to_unreal_python

sample_fountain = """EXT. CYBERPUNK CITY STREET - NIGHT

A wide shot reveals a towering skyscraper. An explosion rocks the lower levels! John sits at a desk.

JOHN
(angry)
I can't believe this is happening!
"""

res = export_to_unreal_python(sample_fountain)
print(f"Direct Call Length: {len(res)}")
print("Sample:")
print(res[:300])
