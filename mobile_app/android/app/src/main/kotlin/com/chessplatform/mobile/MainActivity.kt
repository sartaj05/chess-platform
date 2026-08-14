package com.chessplatform.mobile

import android.content.Intent
import android.os.Bundle
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val channelName = "chess_platform/deep_links"
    private val shareChannelName = "chess_platform/share"
    private var channel: MethodChannel? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
        channel?.setMethodCallHandler { call, result ->
            if (call.method == "getInitialLink") result.success(intent?.dataString)
            else result.notImplemented()
        }
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, shareChannelName)
            .setMethodCallHandler { call, result ->
                if (call.method != "shareResult") {
                    result.notImplemented()
                    return@setMethodCallHandler
                }
                val text = call.argument<String>("text").orEmpty()
                val title = call.argument<String>("title") ?: "Chess Platform result"
                val share = Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"
                    putExtra(Intent.EXTRA_SUBJECT, title)
                    putExtra(Intent.EXTRA_TEXT, text)
                }
                startActivity(Intent.createChooser(share, title))
                result.success(null)
            }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        intent.dataString?.let { channel?.invokeMethod("link", it) }
    }
}
