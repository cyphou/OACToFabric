import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import MigrationList from "./pages/MigrationList";
import MigrationDetail from "./pages/MigrationDetail";
import MigrationWizard from "./pages/MigrationWizard";
import InventoryBrowser from "./pages/InventoryBrowser";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<MigrationList />} />
        <Route path="new" element={<MigrationWizard />} />
        <Route path="migrations/:id" element={<MigrationDetail />} />
        <Route path="migrations/:id/inventory" element={<InventoryBrowser />} />
      </Route>
    </Routes>
  );
}
