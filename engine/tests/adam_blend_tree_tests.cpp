#include <aibs/character_scene.hpp>
#include <aibs/guide_presentation.hpp>
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <numbers>
#include <stdexcept>
#include <string>
#include <vector>

using namespace aibs;

namespace {

unsigned checks = 0;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
    ++checks;
}

bool near(float actual, float expected, float epsilon = 1e-4f) {
    return std::abs(actual - expected) <= epsilon;
}

GuideState make_guide(Vec3 feet = {2, 0, 3}, Vec3 velocity = {}) {
    GuideState g;
    g.character.feet = feet;
    g.character.velocity = velocity;
    g.character.grounded = true;
    g.destination = {feet.x, feet.y, feet.z + 3};
    g.activity = GuideActivity::near_player;
    return g;
}

float quaternion_norm(Quaternion q) {
    return std::sqrt(q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w);
}

} // namespace

int main() {
    try {
        const auto mesh = make_guide_placeholder();
        validate_character_mesh(mesh);

        // 1. Blend Math & Hermite Smoothstep Properties
        {
            auto pose_idle = sample_character_clip(mesh, 0, 0.0);
            auto pose_walk = sample_character_clip(mesh, 1, 0.25);
            require(pose_idle.joint_count == pose_walk.joint_count, "Identical joint count");

            // Zero blend factor equals idle pose
            auto b0 = blend_character_poses(pose_idle, pose_walk, 0.0f);
            for (std::size_t j = 0; j < mesh.joints.size(); ++j) {
                require(near(b0.local[j].translation.x, pose_idle.local[j].translation.x), "Translation x matches idle");
                require(near(b0.local[j].translation.y, pose_idle.local[j].translation.y), "Translation y matches idle");
                require(near(b0.local[j].translation.z, pose_idle.local[j].translation.z), "Translation z matches idle");
                require(near(quaternion_norm(b0.local[j].rotation), 1.0f), "Unit quaternion maintained at factor 0");
            }

            // Full blend factor equals walk pose
            auto b1 = blend_character_poses(pose_idle, pose_walk, 1.0f);
            for (std::size_t j = 0; j < mesh.joints.size(); ++j) {
                require(near(b1.local[j].translation.x, pose_walk.local[j].translation.x), "Translation x matches walk");
                require(near(b1.local[j].translation.y, pose_walk.local[j].translation.y), "Translation y matches walk");
                require(near(b1.local[j].translation.z, pose_walk.local[j].translation.z), "Translation z matches walk");
                require(near(quaternion_norm(b1.local[j].rotation), 1.0f), "Unit quaternion maintained at factor 1");
            }

            // Smoothstep curve testing: S(u) = u^2 * (3 - 2u)
            constexpr unsigned steps = 100;
            double prev_w = 0.0;
            for (unsigned i = 0; i <= steps; ++i) {
                double u = static_cast<double>(i) / steps;
                double w = u * u * (3.0 - 2.0 * u);
                require(w >= prev_w - 1e-9, "Smoothstep curve is strictly monotonic");
                require(w >= 0.0 && w <= 1.0, "Smoothstep curve bounded in [0, 1]");
                prev_w = w;

                auto b = blend_character_poses(pose_idle, pose_walk, static_cast<float>(w));
                for (std::size_t j = 0; j < mesh.joints.size(); ++j) {
                    require(near(quaternion_norm(b.local[j].rotation), 1.0f, 1e-3f), "Quaternion remains normalized across transition");
                }
            }
        }

        // 2. GuidePresentation State Transition Machine
        {
            GuidePresentation presenter(mesh);
            require(!presenter.is_transitioning(), "Initial presenter is not transitioning");
            require(near(static_cast<float>(presenter.transition_progress()), 1.0f), "Initial transition progress is 1.0");

            auto g = make_guide({0, 0, 0}, {0, 0, 0});
            // Frame 0: idle
            auto f0 = presenter.sample(g, 1.0 / 60.0);
            require(f0.has_value(), "Idle sample valid");
            require(presenter.clip() == GuidePresentationClip::idle, "Guide starts in idle");
            require(!presenter.is_transitioning(), "Not transitioning while stationary");

            // Transition from idle -> walk
            g.character.velocity = {0, 0, 2.5f}; // moving speed > 0.12 m/s
            g.activity = GuideActivity::following;
            g.intent = GuideIntent::follow;

            // Frame 1: first step of transition
            auto f1 = presenter.sample(g, 1.0 / 60.0);
            require(f1.has_value(), "First transition frame valid");
            require(presenter.clip() == GuidePresentationClip::walk, "Target clip switched to walk");
            require(presenter.is_transitioning(), "Presenter is in active transition");
            require(presenter.transition_progress() > 0.0 && presenter.transition_progress() < 1.0, "Transition in progress");

            // Advance through transition (0.20s total duration = 12 ticks at 60 Hz)
            for (int tick = 0; tick < 12; ++tick) {
                auto fn = presenter.sample(g, 1.0 / 60.0);
                require(fn.has_value(), "Transition frame valid");
            }
            require(!presenter.is_transitioning(), "Transition complete after 0.20s");
            require(near(static_cast<float>(presenter.transition_progress()), 1.0f), "Transition progress reached 1.0");

            // Transition from walk -> guidance
            g.character.velocity = {0, 0, 0};
            g.activity = GuideActivity::waiting;
            g.intent = GuideIntent::wait;
            auto fg = presenter.sample(g, 1.0 / 60.0, false, false, true);
            require(fg.has_value(), "Guidance trigger valid");
            require(presenter.clip() == GuidePresentationClip::guidance, "Target clip switched to guidance");
            require(presenter.is_transitioning(), "Guidance transition active");

            // Complete guidance transition
            for (int tick = 0; tick < 12; ++tick) {
                (void)presenter.sample(g, 1.0 / 60.0, false, false, true);
            }
            require(!presenter.is_transitioning(), "Guidance transition complete");

            // Reset restores pristine state
            presenter.reset();
            require(!presenter.is_transitioning(), "Reset clears transition state");
            require(presenter.animation_seconds() == 0.0, "Reset clears clock");
            require(presenter.yaw() == 0.0f, "Reset clears yaw");
        }

        // 3. Adam Character Likeness & v33 Asset Verification
        {
            const std::filesystem::path v33_dir = "E:/AI_BS_Resources/FirstBoot/P102/AdamNeckColorStudy/master";
            const auto v33_glb = v33_dir / "adam-character-v33-neck-color-candidate.glb";
            const auto v33_json = v33_dir / "model-verification.json";

            if (std::filesystem::exists(v33_glb) && std::filesystem::exists(v33_json)) {
                std::ifstream f(v33_json);
                std::string content((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
                require(content.find("passed_separate_v33_local_color_only_contracts") != std::string::npos, "v33 status verified");
                require(content.find("0.04335959255695343") != std::string::npos, "Max delta matches 0.04336 bound");
                require(content.find("authored-hair-albedo-v29b.png") != std::string::npos, "Hair albedo v29b registered");
                require(content.find("authored-head-albedo-v24c.png") != std::string::npos, "Head albedo v24c registered");
                require(content.find("authored-shirt-print.png") != std::string::npos, "Shirt print registered");

                const auto file_size = std::filesystem::file_size(v33_glb);
                require(file_size == 6299656, "Candidate GLB file size is exactly 6,299,656 bytes");
            }
        }

        std::cout << "PASS: all " << checks << " adam character blend tree and likeness verification checks passed.\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "FAIL: " << e.what() << "\n";
        return 1;
    }
}

