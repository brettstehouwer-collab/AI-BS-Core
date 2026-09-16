/**
 * AdvertisingTabWrapper — legacy shim.
 *
 * The old god-props architecture passed 130+ props through this wrapper.
 * The app now uses AppContext + direct backendUrl prop injection via App.jsx.
 * This file is kept only to prevent broken imports in any external reference.
 * App.jsx mounts AdvertisingTab directly — this wrapper is no longer in the render tree.
 */
import AdvertisingTab from './AdvertisingTab';
export default AdvertisingTab;
