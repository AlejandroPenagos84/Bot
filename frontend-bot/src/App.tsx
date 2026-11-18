import { Navigate, Route, Routes } from 'react-router'

import LoginPage from '@/pages/LoginPage'
import UsersPage from '@/pages/UsersPage'
import PrivateRoute from '@/router/PrivateRoute'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<PrivateRoute />}>
        <Route path="/" element={<UsersPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
