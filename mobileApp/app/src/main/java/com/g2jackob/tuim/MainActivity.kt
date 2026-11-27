package com.g2jackob.tuim

import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.lifecycle.lifecycleScope
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.g2jackob.tuim.ui.TuimViewModel
import com.g2jackob.tuim.ui.screens.DetailScreen
import com.g2jackob.tuim.ui.screens.ListsScreen
import com.g2jackob.tuim.ui.screens.LoginScreen
import com.g2jackob.tuim.ui.theme.TuimTheme
import com.g2jackob.tuim.data.network.DevelopmentConnectionBuilder
import kotlinx.coroutines.launch
import net.openid.appauth.AuthorizationException
import net.openid.appauth.AuthorizationRequest
import net.openid.appauth.AuthorizationResponse
import net.openid.appauth.AuthorizationService
import net.openid.appauth.AuthorizationServiceConfiguration
import net.openid.appauth.AppAuthConfiguration
import net.openid.appauth.ResponseTypeValues

class MainActivity : ComponentActivity() {
    private val appContainer
        get() = (application as TuimApplication).container

    private val viewModel: TuimViewModel by viewModels {
        TuimViewModel.Factory(appContainer.repository)
    }

    private lateinit var authorizationService: AuthorizationService

    private val authorizationLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            val data = result.data
            if (data == null) {
                viewModel.authFailed("Logowanie zostało przerwane")
            } else {
                val response = AuthorizationResponse.fromIntent(data)
                val exception = AuthorizationException.fromIntent(data)
                if (response == null) {
                    viewModel.authFailed(
                        exception?.errorDescription ?: "Logowanie zostało przerwane"
                    )
                } else {
                    authorizationService.performTokenRequest(response.createTokenExchangeRequest()) {
                            tokenResponse, tokenException ->
                        runOnUiThread {
                            val accessToken = tokenResponse?.accessToken
                            if (accessToken != null) {
                                appContainer.tokenStore.saveConfiguration(
                                    response.request.configuration.tokenEndpoint.toString(),
                                    response.request.clientId
                                )
                                viewModel.completeLogin(accessToken, tokenResponse.refreshToken)
                            } else {
                                viewModel.authFailed(
                                    tokenException?.errorDescription
                                        ?: "Nie udało się uzyskać tokenu"
                                )
                            }
                        }
                    }
                }
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        authorizationService = AuthorizationService(
            this,
            AppAuthConfiguration.Builder()
                .setConnectionBuilder(DevelopmentConnectionBuilder())
                .build()
        )
        setContent {
            TuimTheme {
                val loggedIn by viewModel.isLoggedIn.collectAsState()
                val navController = rememberNavController()
                var previousLoggedIn by remember { mutableStateOf(loggedIn) }
                LaunchedEffect(loggedIn) {
                    if (previousLoggedIn && !loggedIn) {
                        navController.navigate("login") {
                            popUpTo(navController.graph.id) { inclusive = true }
                            launchSingleTop = true
                        }
                    }
                    previousLoggedIn = loggedIn
                }
                NavHost(
                    navController = navController,
                    startDestination = if (loggedIn) "lists" else "login"
                ) {
                    composable("login") {
                        LoginScreen(
                            viewModel = viewModel,
                            onAuthorize = ::startAuthorization,
                            onLoggedIn = {
                                navController.navigate("lists") {
                                    popUpTo("login") { inclusive = true }
                                }
                            }
                        )
                    }
                    composable("lists") {
                        ListsScreen(
                            viewModel = viewModel,
                            tokenStore = appContainer.tokenStore,
                            onOpenList = { listId -> navController.navigate("list/$listId") },
                            onLogout = viewModel::logout
                        )
                    }
                    composable("list/{listId}") { backStackEntry ->
                        val listId = backStackEntry.arguments?.getString("listId").orEmpty()
                        DetailScreen(
                            viewModel = viewModel,
                            listId = listId,
                            tokenStore = appContainer.tokenStore,
                            onBack = { navController.popBackStack() }
                        )
                    }
                }
            }
        }
    }

    private fun startAuthorization() {
        viewModel.authStarted()
        lifecycleScope.launch {
            runCatching { appContainer.api.getAuthConfig() }
                .onSuccess { config ->
                    val serviceConfiguration = AuthorizationServiceConfiguration(
                        Uri.parse(config.authorizationEndpoint),
                        Uri.parse(config.tokenEndpoint)
                    )
                    val request = AuthorizationRequest.Builder(
                        serviceConfiguration,
                        config.clientId,
                        ResponseTypeValues.CODE,
                        Uri.parse(REDIRECT_URI)
                    )
                        .setScopes("openid", "profile", "email")
                        .build()
                    authorizationLauncher.launch(
                        authorizationService.getAuthorizationRequestIntent(request)
                    )
                }
                .onFailure {
                    viewModel.authFailed(it.message ?: "Nie można połączyć się z backendem")
                }
        }
    }

    override fun onDestroy() {
        authorizationService.dispose()
        super.onDestroy()
    }

    private companion object {
        const val REDIRECT_URI = "com.example.shoppinglist:/oauth2redirect"
    }
}
