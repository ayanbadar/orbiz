import { Navigate, Route, Routes } from "react-router-dom";

import { ROUTES } from "@/constants/routes";
import { DemoPage } from "@/features/demo/components/demo-page";

export function App() {
  return (
    <Routes>
      <Route
        path={ROUTES.root()}
        element={<Navigate to={ROUTES.demo.root()} replace />}
      />
      <Route path={ROUTES.demo.root()} element={<DemoPage />} />
      <Route path="*" element={<Navigate to={ROUTES.demo.root()} replace />} />
    </Routes>
  );
}
