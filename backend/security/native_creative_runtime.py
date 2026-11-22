"""Optional reviewed native writer lifecycle; never selects projects or owners."""
from security.native_creative_controller import NativeCreativeController
from security.native_creative_handoff import CreativeHandoffs

_retained_controllers = []


def configure_native_creative(router):
    if router._NATIVE_CREATIVE_CONTROLLER is not None or router._NATIVE_CREATIVE_ADAPTER is not None:
        raise RuntimeError('An existing native controller must not be replaced.')
    from security.native_creative_config import load_reviewed_candidate
    candidate = load_reviewed_candidate()
    if candidate is None:
        return None
    controller = NativeCreativeController.create(candidate, CreativeHandoffs(),
        router._issue_native_creative_grant, capacity=1, services=router)
    # Startup publishes before the API accepts requests. No HTTP operation can
    # alter the manifest, select an executable or replace this controller.
    router._NATIVE_CREATIVE_ADAPTER = controller.adapter
    router._NATIVE_CREATIVE_CONTROLLER = controller
    return controller


def stop_native_creative(router, controller):
    if controller is None:
        return {'complete': True, 'retained_resources': 0, 'pending_launches': 0}
    if router._NATIVE_CREATIVE_CONTROLLER is controller:
        router._NATIVE_CREATIVE_CONTROLLER = None
    if router._NATIVE_CREATIVE_ADAPTER is controller.adapter:
        router._NATIVE_CREATIVE_ADAPTER = None
    try:
        result = controller.shutdown()
    except BaseException:
        if controller not in _retained_controllers:
            _retained_controllers.append(controller)
        raise
    if not result['complete'] and controller not in _retained_controllers:
        _retained_controllers.append(controller)
    elif result['complete'] and controller in _retained_controllers:
        _retained_controllers.remove(controller)
    return result
