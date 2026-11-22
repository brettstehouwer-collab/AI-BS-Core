#pragma once
#include <aibs/gameplay.hpp>
#include <array>
#include <optional>
#include <string_view>
namespace aibs {
inline constexpr std::string_view opening_workshop_hint_key="workshop.binding";
inline constexpr std::string_view opening_workshop_component_type="firstboot.OpeningWorkshop";
inline constexpr std::string_view opening_workshop_reader_capability="chapter-workshop-commissioning-v1";
inline constexpr std::string_view opening_workshop_assembly_component_type="firstboot.WorkshopRelayAssembly";
// Ordered owned fixture UUIDs: probe, supply contact, path contact, tester, bench.
struct OpeningWorkshopBinding {std::array<std::string,5> fixtures;bool operator==(const OpeningWorkshopBinding&)const=default;};
std::string encode_opening_workshop_binding(const OpeningWorkshopBinding&);
OpeningWorkshopBinding decode_opening_workshop_binding(std::string_view);
ComponentSchema opening_workshop_schema();
ComponentRecord opening_workshop_initial(const OpeningWorkshopBinding&);
// Explicit additive runtime family; never changes the original five-field v1.
ComponentSchema opening_workshop_assembly_schema();
ComponentRecord opening_workshop_assembly_record(const OpeningWorkshopBinding&,bool available,bool legacy);
void validate_opening_workshop_assembly(const ComponentRecord&,const OpeningWorkshopBinding&);
void validate_opening_workshop_record(const ComponentRecord&,const OpeningWorkshopBinding&,std::string_view fault_id={});
struct OpeningWorkshopCircuit {
 std::string fault_id,relay_id;
 double capacity=0,relay_capacity=0;
 bool isolated=false,bypass_connected=false,relay_alive=false;
};
// Authoritative source tuple. No voltage/thermal/electrical solver is claimed.
std::string opening_workshop_signature(const OpeningWorkshopCircuit&);
std::string opening_workshop_supply(const OpeningWorkshopCircuit&);
enum class OpeningWorkshopAction {collect_probe,sample_supply,sample_path,test_feed,commission_bench};
struct OpeningWorkshopActor {
 std::string target_id;
 double distance=0;
 bool grounded=true,inspection_mode=false,visible=false,in_shelter=false;
};
struct OpeningWorkshopChange {ComponentRecord component;MechanismOutcome outcome;};
std::optional<OpeningWorkshopChange> plan_opening_workshop(const ComponentRecord&,const OpeningWorkshopBinding&,
 const OpeningWorkshopCircuit&,OpeningWorkshopAction,const OpeningWorkshopActor&);
bool opening_workshop_online(const ComponentRecord&,const OpeningWorkshopBinding&,const OpeningWorkshopCircuit&);
std::string opening_workshop_reading(const OpeningWorkshopCircuit&);
// Read the selected contact's immutable observation, never the present circuit.
// Uses the same owned-record, canonical-stamp and fault-identity validation.
std::optional<std::string> opening_workshop_saved_reading(const ComponentRecord&,const OpeningWorkshopBinding&,
 OpeningWorkshopAction,const std::string& fault_id);
}
