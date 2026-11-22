// Generated SDK demonstration: authoring restart and a CPU-only probe plan.
// No renderer, window, family media, inference or complete chapter playthrough.
#include <aibs/warm_opening.hpp>
#include <aibs/content_authoring.hpp>
#include <aibs/opening_workshop.hpp>
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
namespace fs = std::filesystem;
using namespace aibs;

static void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}
static const FirstBootContentFixture& fixture(const FirstBootContent& content, const std::string& id) {
    const auto& fixtures = content.definition().fixtures;
    const auto found = std::find_if(fixtures.begin(), fixtures.end(), [&](const auto& f) { return f.object.persistent_id == id; });
    require(found != fixtures.end(), "Owned fixture is missing");
    return *found;
}
static FirstBootChapterActor probe_approach(const GameplayStoreRecovery& state, const FirstBootContent& content, const std::string& id) {
    auto scene = first_boot_content_scene(state, content), visibility = scene;
    for (auto& object : visibility.objects) object.selectable = true; // Include ordinary occluders.
    const auto center = fixture(content, id).object.center;
    const auto floor = content.definition().jenison_returns.front().y;
    for (const Vec3 offset : {Vec3{1.2f,0,0}, Vec3{-1.2f,0,0}, Vec3{0,0,1.2f}, Vec3{0,0,-1.2f},
                             Vec3{2.5f,0,0}, Vec3{-2.5f,0,0}, Vec3{0,0,2.5f}, Vec3{0,0,-2.5f}}) {
        try {
            GroundedCharacter body(scene, {center.x + offset.x, floor, center.z + offset.z});
            for (unsigned tick = 0; tick < 24; ++tick) body.advance({}, 1. / 60);
            const auto standing = body.state();
            if (!standing.grounded) continue;
            const Vec3 eye{standing.feet.x, standing.feet.y + .9f, standing.feet.z};
            const auto hit = pick_scene(visibility, eye, {center.x-eye.x, center.y-eye.y, center.z-eye.z}, 3.2f);
            if (hit && hit->persistent_id == id) {
                FirstBootChapterActor actor; actor.feet = actor.previous_feet = standing.feet; actor.grounded = true;
                return actor;
            }
        } catch (const std::invalid_argument&) {} // Try the next bounded local approach.
    }
    throw std::runtime_error("No clear grounded probe approach");
}
static void write_content(const fs::path& path, const std::vector<unsigned char>& bytes) {
    std::ofstream file(path, std::ios::binary);
    file.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
    file.close(); require(file.good(), "Cannot write owned example content");
}
int main(int argc, char** argv) {
    try {
        require(argc == 2, "Usage: opening_workshop_example NEW_OUTPUT_DIRECTORY");
        const auto output = fs::absolute(argv[1]).lexically_normal();
        require(!fs::exists(output) && fs::is_directory(output.parent_path()) && !output.filename().empty(),
                "Refusing existing output; choose a new child of an existing directory");
        CreatorSession source(first_boot_schema(), "sdk-opening-workshop", "example");
        require(seed_first_boot(source).ok, "Cannot seed the new example session");
        const auto original_world = source.world();
        const auto draft = make_warm_workshop_draft(source, {}); // No optional asset/media dependencies.
        require(source.world() == original_world, "Factory changed its source session");
        const auto content = FirstBootContent::create(draft.definition);
        const auto binding = first_boot_content_workshop_binding(content.definition());
        require(binding.has_value() && content.definition().format_version == 3, "Missing v3 Workshop binding");
        require(decode_opening_workshop_binding(encode_opening_workshop_binding(*binding)) == *binding,
                "Five-action binding roundtrip changed ownership");
        for (const auto& id : binding->fixtures)
            require(fixture(content,id).role == FixtureRole::workshop, "Bound fixture lost its role");
        const auto bytes = first_boot_content_encode(content);
        const auto decoded = first_boot_content_decode(bytes);
        require(decoded.fingerprint() == content.fingerprint() && first_boot_content_encode(decoded) == bytes,
                "AIBD3 roundtrip changed content");

        GameplayScope scope{source.project_id(), source.world_id(), source.branch_id(), new_uuid(), GameplayContext::player_world};
        const GameplayStoreRecovery state{scope, 0, 0, first_boot_content_baseline(content).components};
        const auto actor = probe_approach(state, content, binding->fixtures[0]);
        FirstBootChapterCommand command; command.action = FirstBootChapterAction::collect_probe;
        command.target_id = binding->fixtures[0]; command.operation_id = "sdk.probe." + new_uuid();
        const auto before = state.components;
        const auto batch = first_boot_content_action(state, command, actor, content);
        require(batch.has_value() && state.components == before, "Probe plan missing or source state mutated");
        const auto current = std::find_if(before.begin(), before.end(), [&](const auto& c) {
            return c.entity_id == binding->fixtures[4] && c.type_id == opening_workshop_component_type; });
        require(current != before.end(), "Conditional Workshop baseline component is missing");
        const auto center = fixture(content,binding->fixtures[0]).object.center;
        const double dx = center.x-actor.feet.x, dy = center.y-(actor.feet.y+.9f), dz = center.z-actor.feet.z;
        OpeningWorkshopActor observed{command.target_id, std::sqrt(dx*dx+dy*dy+dz*dz), actor.grounded, false, true, false};
        const auto plan = plan_opening_workshop(*current, *binding, first_boot_content_workshop_circuit(state,content),
                                               OpeningWorkshopAction::collect_probe, observed);
        require(plan.has_value() && std::get<bool>(plan->component.fields.at("has_probe")), "Owned probe rule rejected");
        require(std::any_of(batch->deltas.begin(), batch->deltas.end(), [&](const auto& d) {
            return d.component == plan->component; }), "Chapter plan differs from public Workshop rule");

        const auto temporary = output.parent_path() / (output.filename().string() + ".staging-" + new_uuid());
        require(fs::create_directory(temporary), "Cannot create a fresh staging directory");
        const auto journal = temporary / "chapter.aiba";
        {
            ContentAuthoringHost owner(content, source.project_id(), source.branch_id());
            require(owner.save(journal).status == ContentAuthoringStatus::saved, "New authoring Save failed");
        }
        {
            auto reopened = ContentAuthoringHost::open(journal, source.project_id(), source.branch_id());
            require(reopened.snapshot()->content.fingerprint() == content.fingerprint(), "New owner restart changed fingerprint");
        }
        write_content(temporary / "opening.aibd", bytes);
        // The probe action was planned only. It is never injected into authored progress.
        std::ofstream report(temporary / "example.json");
        report << "{\"generated_sdk_demo\":true,\"sdk\":\"0.15.0\",\"binding_count\":5,\"format_version\":3,"
               << "\"probe_fixture_id\":\"" << binding->fixtures[0] << "\",\"bench_fixture_id\":\"" << binding->fixtures[4] << "\","
               << "\"fingerprint\":\"" << content.fingerprint() << "\",\"restart_verified\":true,\"probe_plan_only\":true,"
               << "\"full_chapter_runtime_verified\":false,\"pacing_measured\":false,\"renderer_called\":false}\n";
        report.close(); require(report.good(), "Cannot write example report");
        require(!fs::exists(output), "Output appeared during staging; preserving both directories");
        fs::rename(temporary, output);
        std::cout << "Created SDK0.15 Workshop example: restart and owned probe plan verified.\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\nA failed example staging directory is retained for diagnostics.\n";
        return 1;
    }
}
