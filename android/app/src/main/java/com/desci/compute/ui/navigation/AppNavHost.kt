package com.desci.compute.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.desci.compute.ui.screens.AuthScreen
import com.desci.compute.ui.screens.CampaignArenaScreen
import com.desci.compute.ui.screens.DashboardScreen
import com.desci.compute.ui.screens.LeaderboardScreen
import com.desci.compute.ui.screens.ProfileScreen
import com.desci.compute.ui.viewmodel.AuthViewModel

@Composable
fun AppNavHost() {
    val navController = rememberNavController()
    val authViewModel: AuthViewModel = hiltViewModel()
    val authState by authViewModel.state.collectAsState()

    val startDest = if (authState.isLoggedIn) "dashboard" else "auth"

    NavHost(navController = navController, startDestination = startDest) {
        composable("auth") {
            AuthScreen(
                viewModel = authViewModel,
                onLoginSuccess = {
                    navController.navigate("dashboard") {
                        popUpTo("auth") { inclusive = true }
                    }
                }
            )
        }
        composable("dashboard") {
            DashboardScreen(
                onNavigateToLeaderboard = { navController.navigate("leaderboard") },
                onNavigateToProfile = { navController.navigate("profile") },
                onNavigateToCampaigns = { navController.navigate("campaigns") },
            )
        }
        composable("campaigns") {
            CampaignArenaScreen(
                onBack = { navController.popBackStack() },
            )
        }
        composable("leaderboard") {
            LeaderboardScreen(onBack = { navController.popBackStack() })
        }
        composable("profile") {
            ProfileScreen(
                authViewModel = authViewModel,
                onLogout = {
                    authViewModel.logout()
                    navController.navigate("auth") {
                        popUpTo(0) { inclusive = true }
                    }
                },
                onBack = { navController.popBackStack() },
            )
        }
    }
}
