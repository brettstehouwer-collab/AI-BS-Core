# AI-BS Creator quickstart

**Available: v5.329.98 / SDK0.11.** The five existing desktop and Start menu shortcuts now open this verified release. Close an older Studio window normally, then reopen your shortcut to use98.

1. Open Studio, then choose **Engineering & Specialized Labs → AI-BS Game Engine Build → Chapter creator**. The adjacent **Creator** tab is the numeric world workspace; typed chapter editing and the local AI prompt are in **Chapter creator**.
2. Create an empty folder you own, for example `C:\Users\footb\Documents\AI-BS-Projects\MyChapter`. Click **New project**, select that existing folder, and enter a project identifier. Keep your work outside acceptance-test scratch folders. To resume a saved chapter, click **Open project** and select its folder.
3. Select an object in the outliner. To add one, enter a **New fixture name**, click **Add fixture**, and select it. Edit its text, number, or checkbox fields in **Inspector**. Click **Preview change**, review the proposed changes, then **Apply preview**. Click **Save chapter** to persist them; Apply and Save are separate steps. **Undo** and **Redo** operate on applied edits.

## Use a local AI proposal

1. Keep the chapter open and select the object to change.
2. In **Local AI authoring — selected object**, click **Refresh models**. Choose the installed **qwen2.5-coder:latest** model. Discovery checks local Ollama at `127.0.0.1:11434` and `127.0.0.1:11435`; Studio does not download models, and model weights are not bundled.
3. Describe one change to an exposed field, for example: “Rename the selected fixture to My first scene. Change only its name field.” Click **Generate proposal**.
4. Wait for the native preview, review every proposed before/after value, then click **Apply preview → Save chapter**. Generation alone changes neither the authored document nor the saved file. A changed selection or editing context can invalidate the proposal; generate a fresh one when needed.

AI authoring proposes text, number, and boolean field changes for the selected object. Validation covers one installed model and one explicit field-change request; it does not establish a universal game builder. Treat generated memoir wording as draft prose; it does not recover Adam's memories.

## Preview and Play

Click **Open chapter preview** for the native 3D window. Click **Play chapter** to test an immutable snapshot in an isolated Play workspace. **Stop Play** resets test gameplay changes while preserving creator edits. Save authored changes with **Save chapter**, and use **Close project** when finished.

## Persistent motherboard parts (SDK 0.10 placement workflow)

Release verification and launcher availability are recorded at the top of this guide. The placement workflow is in **Chapter creator**, separate from the standalone **Assets** inspection tab.

1. Open or create your chapter project. Click **Use bundled sample part**, or **Open asset pack → Copy asset to project** for your own cooked pack. Copying preserves the exact geometry, catalog, license and provenance inside the chapter project; it does not place an object yet.
2. Enter a placement name and click **Preview asset placement**. Review the native dependency preview, then click **Apply preview**. Select the new `authoring.AssetPlacement` row in the outliner.
3. Edit position (`x/y/z`), positive scale (`scale_x/y/z`) or unit quaternion rotation (`rotation_x/y/z/w`) in Inspector. Each field edit uses **Preview change → Apply preview**. Identity and dependency hashes are read-only. Open the chapter preview to see applied changes; mouse selection uses the part's bounding box.
4. Click **Save chapter**, then close and reopen the project. The placement keeps its UUID, transform and pinned pack. Undo/Redo and **Delete placement** use the same native authoring history. Deleting the final placement retains the new document format.
5. **Play chapter** stages an isolated copy of the currently referenced packs. **Stop Play** closes the owned player and removes that test workspace. Gameplay testing does not rewrite creator placements.

Back up the **whole chapter folder**, including `.aibs-chapter-project.json`, `chapter.aiba` and `assets/packs`. Keep old immutable packs: Undo/Redo can still reference them. A missing or changed pack blocks publication/Play with a diagnostic; reopening still exposes the authored rows so you can restore the exact dependency or explicitly remove the placement.

Placements currently affect visuals and editor picking. They do not add physics collision, sockets, snapping or resource costs. Existing saved AIBD1 chapters remain readable; the first applied placement creates AIBD2 content. Use a new compatible Studio/SDK for the new content rather than opening it in an older release.


## Character packs in the Warm Beginning workshop

In a Warm Beginning chapter that declares an Adam companion binding, open a verified character pack and copy it into the project. **Preview Adam model** prepares one complete model assignment. Review it, then use **Apply preview → Save chapter**. Model references remain read-only; ordinary AI proposals can adjust exposed companion name, spawn and following fields. The imported model includes its own textures and four named animation clips. Chapter Preview and isolated Play stage that complete dependency closure. Generic static placement remains a separate action.

Blender is the modeling workshop. Its live MCP connection needs Blender and the add-on server running; command-line modeling/export can run in a background Blender process. Current engine acceptance uses synthetic characters. Adam’s podium-inspired likeness and the finished personal opening remain in progress.
