import { BrowserRouter, Routes, Route } from "react-router-dom";
import Login from "./pages/Login";

import ProtectedRoute from "./routes/ProtectedRoute";

import MainLayout from "./layouts/MainLayout";

import Dashboard from "./pages/Dashboard";
import StockMasterPage from "./pages/stocks/StockMasterPage";
import FinancialFactsPage from "./pages/stocks/FinancialFactsPage";
import MetricsPage from "./pages/stocks/MetricsPage";
import StatementsPage from "./pages/stocks/StatementsPage";
import DatesPage from "./pages/stocks/DatesPage";
import StockExplorerPage from "./pages/stocks/StockExplorerPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<MainLayout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/stocks/master" element={<StockMasterPage />} />
            <Route path="/stocks/dates" element={<DatesPage />} />
            <Route path="/stocks/statements" element={<StatementsPage />} />
            <Route path="/stocks/metrics" element={<MetricsPage />} />
            <Route path="/stocks/facts" element={<FinancialFactsPage />} />
            <Route path="/stocks/explorer" element={<StockExplorerPage />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;