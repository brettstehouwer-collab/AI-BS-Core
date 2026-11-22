import React from 'react';
import { createRoot } from 'react-dom/client';
import PersonalFinancePortal from '../src/personal-finance/PersonalFinancePortal.jsx';
import '../src/personal-finance/personal.css';
createRoot(document.getElementById('root')).render(<PersonalFinancePortal />);
