import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import AdminShell from './AdminShell';

createRoot(document.getElementById('admin-root')).render(
  <BrowserRouter basename="/admin">
    <AdminShell />
  </BrowserRouter>
);
