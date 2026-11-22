#pragma once
#include <aibs/engine.hpp>
#include <aibs/scene.hpp>

namespace aibs {
// Independent SDK sample: authored, persisted motherboard traversal surfaces.
// It does not alter the First Boot project, schema or personal campaign saves.
SchemaRegistry movement_course_schema();
Result seed_movement_course(CreatorSession& session);
SceneSnapshot movement_course_scene(const CreatorSession& session);
Result restore_movement_course(CreatorSession& session, const std::string& persistent_id);
}
