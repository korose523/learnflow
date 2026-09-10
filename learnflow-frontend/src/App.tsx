import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import Layout from './components/common/Layout';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { Skeleton } from './components/common/Skeleton';

// 路由懒加载（Spec AC8：首屏仅登录，其余按需加载）
const StudentDashboard = lazy(() => import('./pages/StudentDashboard'));
const LearningSession = lazy(() => import('./pages/LearningSession'));
const LearnPage = lazy(() => import('./pages/LearnPage'));
const TeacherDashboard = lazy(() => import('./pages/TeacherDashboard'));
const TeacherPage = lazy(() => import('./pages/TeacherPage'));
const ParentSummary = lazy(() => import('./pages/ParentSummary'));
const ParentPage = lazy(() => import('./pages/ParentPage'));
const AdminPanel = lazy(() => import('./pages/AdminPanel'));
const SkillTreePage = lazy(() => import('./pages/SkillTreePage'));
const StreakPage = lazy(() => import('./pages/StreakPage'));
const PetCustomizePage = lazy(() => import('./pages/PetCustomizePage'));
const ClassPetGardenPage = lazy(() => import('./pages/ClassPetGardenPage'));
const StudentRiskPage = lazy(() => import('./pages/StudentRiskPage'));
const TeacherAnalyticsPage = lazy(() => import('./pages/TeacherAnalyticsPage'));
const TeamPage = lazy(() => import('./pages/TeamPage'));
const CurriculumPage = lazy(() => import('./pages/CurriculumPage'));
const OnboardingPage = lazy(() => import('./pages/OnboardingPage'));
const LeaderboardPage = lazy(() => import('./pages/LeaderboardPage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));

// 骨架屏 fallback（童趣圆角）
function RouteFallback() {
  return (
    <div style={{ maxWidth: 900, margin: '0 auto', display: 'grid', gap: 16 }}>
      <Skeleton width="40%" height={28} rounded="lg" />
      <Skeleton height={120} rounded="lg" />
      <Skeleton height={200} rounded="lg" />
      <Skeleton height={160} rounded="lg" />
    </div>
  );
}

function App() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        {/* 登录页 — 已登录用户自动跳转到对应 dashboard */}
        <Route path="/login" element={<LoginPage />} />
        {/* 新用户引导（独立全屏，无需先登录完成引导） */}
        <Route path="/onboarding" element={<OnboardingPage />} />

        {/* 受保护的路由 — 所有页面需认证 */}
        <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route index element={<Navigate to="/student" replace />} />

          {/* 学生端 */}
          <Route path="student" element={<ProtectedRoute allowedRoles={['student']}><StudentDashboard /></ProtectedRoute>} />
          <Route path="student/learn" element={<ProtectedRoute allowedRoles={['student']}><LearningSession /></ProtectedRoute>} />
          <Route path="learn" element={<ProtectedRoute allowedRoles={['student']}><LearnPage /></ProtectedRoute>} />
          <Route path="student/skill-tree" element={<ProtectedRoute allowedRoles={['student']}><SkillTreePage /></ProtectedRoute>} />
          <Route path="student/streak" element={<ProtectedRoute allowedRoles={['student']}><StreakPage /></ProtectedRoute>} />
          <Route path="student/team" element={<ProtectedRoute allowedRoles={['student']}><TeamPage /></ProtectedRoute>} />
          <Route path="student/pet" element={<ProtectedRoute allowedRoles={['student']}><PetCustomizePage /></ProtectedRoute>} />
          <Route path="student/class-pet" element={<ProtectedRoute allowedRoles={['student']}><ClassPetGardenPage /></ProtectedRoute>} />
          <Route path="student/ai-risk" element={<ProtectedRoute allowedRoles={['student']}><StudentRiskPage /></ProtectedRoute>} />
          <Route path="student/leaderboard" element={<ProtectedRoute allowedRoles={['student']}><LeaderboardPage /></ProtectedRoute>} />
          <Route path="curriculum" element={<ProtectedRoute allowedRoles={['student', 'teacher', 'parent']}><CurriculumPage /></ProtectedRoute>} />

          {/* 教师端 */}
          <Route path="teacher" element={<ProtectedRoute allowedRoles={['teacher']}><TeacherDashboard /></ProtectedRoute>} />
          <Route path="teacher/class-pet" element={<ProtectedRoute allowedRoles={['teacher']}><ClassPetGardenPage /></ProtectedRoute>} />
          <Route path="teacher/assign" element={<ProtectedRoute allowedRoles={['teacher']}><TeacherPage /></ProtectedRoute>} />
          <Route path="teacher/ai-analytics" element={<ProtectedRoute allowedRoles={['teacher']}><TeacherAnalyticsPage /></ProtectedRoute>} />

          {/* 家长端 */}
          <Route path="parent" element={<ProtectedRoute allowedRoles={['parent']}><ParentPage /></ProtectedRoute>} />
          <Route path="parent/summary" element={<ProtectedRoute allowedRoles={['parent']}><ParentSummary /></ProtectedRoute>} />

          {/* 管理端 */}
          <Route path="admin" element={<ProtectedRoute allowedRoles={['admin']}><AdminPanel /></ProtectedRoute>} />
        </Route>

        {/* 404 */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  );
}

export default App;
