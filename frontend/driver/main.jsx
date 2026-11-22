import React from 'react';
import { createRoot } from 'react-dom/client';
import DriverPortal from '../src/fe-express/DriverPortal.jsx';
import '../src/fe-express/driver.css';

createRoot(document.getElementById('root')).render(<DriverPortal />);
