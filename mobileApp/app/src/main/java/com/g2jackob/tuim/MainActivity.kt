package com.g2jackob.tuim

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.g2jackob.tuim.ui.TuimViewModel
import com.g2jackob.tuim.ui.screens.DetailScreen
import com.g2jackob.tuim.ui.screens.ListsScreen
import com.g2jackob.tuim.ui.screens.LoginScreen
import com.g2jackob.tuim.ui.theme.TuimTheme

class MainActivity : ComponentActivity() {
    private val viewModel: TuimViewModel by viewModels {
        val app = application as TuimApplication
        TuimViewModel.Factory(app.container.repository)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            TuimTheme {
                val loggedIn by viewModel.isLoggedIn.collectAsState()
                val navController = rememberNavController()
                NavHost(
                    navController = navController,
                    startDestination = if (loggedIn) "lists" else "login"
                ) {
                    composable("login") {
                        LoginScreen(viewModel) {
                            navController.navigate("lists") {
                                popUpTo("login") { inclusive = true }
                            }
                        }
                    }
                    composable("lists") {
                        ListsScreen(
                            viewModel = viewModel,
                            onOpenList = { listId -> navController.navigate("list/$listId") },
                            onLogout = {
                                viewModel.logout()
                                navController.navigate("login") {
                                    popUpTo("lists") { inclusive = true }
                                }
                            }
                        )
                    }
                    composable("list/{listId}") { backStackEntry ->
                        val listId = backStackEntry.arguments?.getString("listId").orEmpty()
                        DetailScreen(
                            viewModel = viewModel,
                            listId = listId,
                            tokenStore = (application as TuimApplication).container.tokenStore,
                            onBack = { navController.popBackStack() }
                        )
                    }
                }
            }
        }
    }
}
