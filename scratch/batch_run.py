import unreal

import unreal

# Spawn a CineCameraActor and set its label to "MainCamera"
camera_bp = unreal.EditorAssetLibrary.load_asset('/Game/Engine/Blueprints/BP_CineCameraActor')
camera_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(camera_bp, unreal.Vector(0, 0, 100), unreal.Rotator(0, 0, 0))
camera_actor.set_editor_property('label', 'MainCamera')

# Save the current level
unreal.EditorLoadingAndSavingUtils.save_current_level()


# --- AUTO-GENERATED MRQ RENDER BOILERPLATE ---
import unreal
import os

def render_sequence():
    print("🎬 [MRQ] Setting up Movie Render Queue...")
    # Get all actors
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    main_camera = None
    for actor in actors:
        if actor.get_actor_label() == "MainCamera":
            main_camera = actor
            break
            
    if not main_camera:
        print("⚠️ [MRQ WARNING] No MainCamera found. Render may fail or use default view.")
        return
        
    print("🎬 [MRQ] Found MainCamera. Creating Level Sequence...")
    
    # 1. Create Sequence
    factory = unreal.LevelSequenceFactoryNew()
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    
    seq_name = "AutoRenderSeq"
    seq_path = "/Game/Sequences"
    sequence = asset_tools.create_asset(seq_name, seq_path, unreal.LevelSequence, factory)
    
    if not sequence:
        print("❌ [MRQ ERROR] Failed to create Level Sequence.")
        return
        
    sequence.set_playback_start(0)
    sequence.set_playback_end(150) # 5 seconds at 30fps
    
    # 2. Add Camera to Sequence
    binding = sequence.add_possessable(main_camera)
    
    # Add Camera Cut Track
    camera_cut_track = sequence.add_master_track(unreal.MovieSceneCameraCutTrack)
    camera_cut_section = camera_cut_track.add_section()
    camera_cut_section.set_range(0, 150)
    
    camera_binding_id = unreal.MovieSceneObjectBindingID()
    camera_binding_id.set_editor_property("guid", binding.get_id())
    camera_cut_section.set_camera_binding_id(camera_binding_id)
    
    # Save the sequence
    unreal.EditorAssetLibrary.save_asset(sequence.get_path_name())
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    
    print("🎬 [MRQ] Level Sequence created. Triggering Render Queue...")
    
    # 3. Setup Movie Render Queue
    subsystem = unreal.get_engine_subsystem(unreal.MoviePipelineQueueEngineSubsystem)
    queue = subsystem.get_queue()
    queue.delete_all_jobs()
    
    job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
    job.sequence = unreal.SoftObjectPath(sequence.get_path_name())
    job.map = unreal.SoftObjectPath(unreal.EditorLevelLibrary.get_editor_world().get_path_name())
    
    config = job.get_configuration()
    output_setting = config.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    
    out_path = r"E:\AI-BS\test_render_async.mp4"
    out_dir = os.path.dirname(out_path)
    out_file = os.path.basename(out_path).split('.')[0]
    
    output_setting.output_directory = unreal.DirectoryPath(out_dir)
    output_setting.file_name_format = out_file
    
    # Add a standard deferred pass so it actually renders image data
    config.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
    
    # Note: For .mp4 export, you'd add the AppleProRes or Command Line Encoder setting here
    # config.find_or_add_setting_by_class(unreal.MoviePipelineCommandLineEncoderSetting)
    
    # 4. Execute Render
    executor = subsystem.render_queue_with_executor(unreal.MoviePipelinePIEExecutor)
    
    # Keep the editor alive until the render finishes
    def on_render_finished(exec, success):
        print(f"✅ [MRQ] Render Finished! Success: {success}")
        unreal.SystemLibrary.quit_editor()
        
    executor.on_executor_finished_delegate.add_callable(on_render_finished)
    print(f"✅ [MRQ] Render job submitted to executor! Check output directory: {out_dir}")
    
    # We use a ticking loop to prevent the python script from hitting EOF and crashing the editor prematurely
    def tick_wait(delta_time):
        pass # The delegate will handle quitting the editor
        
    unreal.register_slate_post_tick_callback(tick_wait)

render_sequence()
