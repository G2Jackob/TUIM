package com.g2jackob.tuim

import android.content.Context
import androidx.room.Room
import com.g2jackob.tuim.data.local.AppDatabase
import com.g2jackob.tuim.data.local.TokenStore
import com.g2jackob.tuim.data.network.ApiService
import com.g2jackob.tuim.data.network.AuthInterceptor
import com.g2jackob.tuim.data.repository.ShoppingRepository
import com.g2jackob.tuim.data.repository.ShoppingRepositoryImpl
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class AppContainer(context: Context) {
    val tokenStore = TokenStore(context)

    val database: AppDatabase = Room.databaseBuilder(
        context,
        AppDatabase::class.java,
        "tuim.db"
    ).fallbackToDestructiveMigration().build()

    private val logging = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BASIC
    }

    private val okHttp: OkHttpClient = OkHttpClient.Builder()
        .addInterceptor(AuthInterceptor(tokenStore))
        .addInterceptor(logging)
        .build()

    val api: ApiService = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .client(okHttp)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(ApiService::class.java)

    val repository: ShoppingRepository = ShoppingRepositoryImpl(database, api, tokenStore)
}
