#include <aibs/engine.hpp>
#include <cmath>
#include <utility>

namespace aibs {
bool SchemaRegistry::add(FieldSchema schema) {
 if (schema.id.empty() || !std::isfinite(schema.minimum) || !std::isfinite(schema.maximum) || schema.minimum > schema.maximum) return false;
 const auto id = schema.id;
 return fields_.emplace(id, std::move(schema)).second;
}
bool SchemaRegistry::accepts(const std::string& field, double value) const {
 const auto it = fields_.find(field);
 return it != fields_.end() && std::isfinite(value) && value >= it->second.minimum && value <= it->second.maximum;
}
}
