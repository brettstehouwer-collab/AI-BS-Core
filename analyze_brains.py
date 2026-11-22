import os, json
import glob

base = r'C:\Users\footb\.gemini\antigravity-ide\brain'
dirs = [
"2ac9501e-8a07-458e-b522-e1a61ab03a32",
"tempmediaStorage",
"eb7f2fc0-1a12-4cc2-8dcd-7183d1072c96",
"3aae2718-d524-42d8-a733-89ca01d44f80",
"6b3665cb-f498-4d66-9ef6-eb5ddee2f4cb",
"437115e5-5d97-4681-8487-8fcc4d32da73",
"66a76b78-898d-4f0e-bfcf-d15852f8e3fc",
"2a4cd234-1f22-4da8-9570-7722aad54b71",
"4a80712f-c17a-4b4c-b09a-5974fbd63d2d",
"2748ab81-5e2e-4b2d-9727-54dc2c0058a1",
"eb5b1a40-4bc0-4e2e-834c-c5cb7e3e54eb",
"c2edc56e-50fd-4880-9045-65764320e4b8",
"81ee1b99-5617-4ece-abb5-ded54bcccfc7",
"7884f40b-dc84-4745-9400-4f03664da890",
"7a25295d-2f8f-4db6-9342-df30d795358c",
"4b548763-501b-4092-a98f-3ec07ea72291",
"b24d0027-d6a3-404f-9ff9-1eaaccd09f24",
"d4177269-68d7-4d39-99c3-2e084452f3d0",
"1c44be2e-1cc4-44e8-a916-e053b2fbbf7b",
"d21bc9fa-021b-4e94-a413-3d94753453ad",
"7ec24639-23c8-4029-98d8-316f9a613d5e",
"bdb10743-773a-4f4e-b103-dec89790596c",
"a556e409-e894-41ae-961d-f33ca98e200f",
"9ea6f83a-093a-4f23-9287-967b4bbf0a61",
"9d2b5e64-868f-4ec1-a63d-87c629b0eb3c",
"b51a519f-093b-49bf-8232-c3ef5fcdeb0c",
"bc5bb536-bea0-4991-98d1-23948761f9be",
"fcb5096c-26c3-4bc2-8044-cc7d26e0a710",
"c05366e1-df52-439a-a1f6-987a0ff9df11",
"4fd175b5-1896-4eb2-9bdd-c9ba93321251",
"9cb23e16-009c-47d5-8924-67b70832fd79",
"6d671b63-3332-428d-8b99-a9f88d82af2d",
"e15adcba-30b3-4dec-aa16-53c3d4481774",
"7fe7421d-945d-4896-abd4-547a7fa05ebb",
"350981ca-ce41-4700-bb88-2656912c1238",
"91153813-e464-47cc-87c9-1cc2972400ef",
"f6cca01b-8544-4f88-b11a-b70e4e5efbbf",
"ffff7803-babf-4317-b3a8-f2d72fe52cd4",
"d8a73088-f013-49a6-821c-de468981bb78",
"d8407438-d894-427d-a147-e0e4527c48f8",
"60d65a70-5112-4cb9-b472-0470e7f13c4c",
"7b0c1e70-73c7-42cd-8b92-da7e5896e3f6",
"0fcc2b02-231e-41ae-8f4e-e0e90b3f74ac",
"27ac3206-71b3-4ac4-b020-19d61ccb0570",
"d6a6ca0b-8594-4480-9e3c-e66aa275d5e9",
"f9b02831-09c1-4669-956d-33b8392707a4",
"1dd91e45-8dc0-43c0-8a6d-ee68da8d93c6",
"1546ffa0-acb1-4ce5-bd20-31c88bf3380b",
"23ba623f-e59b-41e2-a556-7871cca319e8",
"ef32a8bd-fc49-4c9e-acf2-673dbec063c0",
"8cde205e-ab47-485c-8cea-71b2888e9f47",
"729e1e7a-851b-4f02-9c60-134e6f2af3bd",
"00372bb5-300a-4e2a-b3a6-f27f2efead86",
"e809d2b5-6561-48d3-8310-56ed550301f7",
"96ada08f-9faa-4f32-9a18-eae5a2839b9f",
"a96f2d7d-3aeb-4b26-b55b-862c19e847f3",
"f5b145c7-b0d8-44bd-929f-82082f12daa8",
"16effffd-b495-4988-889e-a978595ece04",
"732106dc-1cc4-4dfe-bab6-0fc6940c6439",
"5d2398b8-3209-4aa7-9c66-cd2b6870c3c4",
"86c3414e-094b-4332-831e-507b50037507",
"9e4b6ccc-a7b2-44b4-b181-a18f024066f9",
"ee2d159e-22ef-49b8-8a29-b73ffabdac5e",
"c8affcee-9aab-4f62-881d-6ff71e0f2f57",
"f07c600f-5825-45b4-bdd2-498ac5faa1de",
"b753766f-9823-4943-8eaa-311fad8a573d",
"0f57ae6a-350c-456f-95b9-202bb697f1f9",
"181a0f3d-3f64-40bd-a82f-b97ac370ad9b",
"0d559a36-1a8c-4e50-b194-694c1690ca16",
"f50eab29-ea98-4380-85ae-959a32043abf",
"d2c1412a-1de6-47fe-a455-8298426b232f",
"3ae7a8a4-1f36-45c0-a08c-dcf2c74b5525",
"53e3e424-aa90-45cb-9acd-88f0bd848cd0",
"3b2033b8-1a66-4c5e-9c7c-1d7cd3b1191a",
"a06fdd08-0927-49ce-b21c-f253988ddad6",
"aaf63d8c-fc07-480d-8f4f-fd6a23d8fefa",
"219c7fe4-8b79-486a-8900-8194d245b05c"
]

results = []
for d in dirs:
    path = os.path.join(base, d, "walkthrough.md")
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract first few lines or headers
            summary = "\n".join([line for line in content.split('\n') if line.startswith('#') or line.startswith('-')][:5])
            results.append(f"--- Brain {d} ---\n{summary}")
    else:
        # check transcript for last USER_INPUT
        transcript = os.path.join(base, d, ".system_generated", "logs", "transcript.jsonl")
        if os.path.exists(transcript):
            try:
                with open(transcript, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    last_user = ""
                    for line in reversed(lines):
                        try:
                            obj = json.loads(line)
                            if obj.get('type') == 'USER_INPUT':
                                last_user = obj.get('content', '')[:100]
                                break
                        except:
                            pass
                    results.append(f"--- Brain {d} ---\nNo walkthrough. Last user prompt: {last_user}")
            except:
                pass

with open('C:/AI-BS/brain_summary.txt', 'w', encoding='utf-8') as f:
    f.write("\n".join(results))
