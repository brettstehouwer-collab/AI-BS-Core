import unreal

import unreal

# Create a new level
level = unreal.EditorLevelLibrary.load_current_level()

# Spawn the noodle stand actor
noodle_stand = unreal.ActorFactory.spawn_actor_class("NoodleStand", unreal.Transform(location=(0, 0, 0), rotation=(0, 0, 0)))
noodle_stand.set_name("Neon Noodle Stand")

# Set the noodle stand's label
label = unreal.EditorLabelLibrary.create_label(noodle_stand)
label.set_text("Neon Noodles")
label.set_font_size(20)

# Spawn a neon sign actor
neon_sign = unreal.ActorFactory.spawn_actor_class("NeonSign", unreal.Transform(location=(0, 1.5, 0), rotation=(0, 0, 0)))
neon_sign.set_name("Neon Sign")

# Set the neon sign's label
label = unreal.EditorLabelLibrary.create_label(neon_sign)
label.set_text("Fresh Noodles")
label.set_font_size(30)

# Spawn a street light actor
street_light = unreal.ActorFactory.spawn_actor_class("StreetLight", unreal.Transform(location=(0, 2.5, 0), rotation=(0, 0, 0)))
street_light.set_name("Street Light")

# Set the street light's label
label = unreal.EditorLabelLibrary.create_label(street_light)
label.set_text("")
label.set_font_size(20)

# Save the current level
unreal.EditorLoadingAndSavingUtils.save_current_level()