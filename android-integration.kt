// Kotlin code for MITV Android app
// Add to your MainActivity or ChannelRepository

import okhttp3.OkHttpClient
import okhttp3.Request
import kotlinx.coroutines.*

class MITVPanelClient(
    private val panelUrl: String = "https://your-panel.vercel.app"
) {
    private val client = OkHttpClient()

    data class Channel(
        val name: String,
        val streamUrl: String,
        val logo: String,
        val category: String
    )

    suspend fun fetchChannelsFromM3U(username: String, password: String): List<Channel> {
        return withContext(Dispatchers.IO) {
            try {
                val url = "$panelUrl/get.php?username=$username&password=$password&type=m3u_plus&output=m3u8"
                val request = Request.Builder()
                    .url(url)
                    .build()

                val response = client.newCall(request).execute()
                if (!response.isSuccessful) {
                    return@withContext emptyList()
                }

                val m3uContent = response.body?.string() ?: return@withContext emptyList()
                parseM3U(m3uContent)
            } catch (e: Exception) {
                e.printStackTrace()
                emptyList()
            }
        }
    }

    private fun parseM3U(content: String): List<Channel> {
        val channels = mutableListOf<Channel>()
        val lines = content.split("\n")

        var i = 0
        while (i < lines.size) {
            val line = lines[i].trim()

            // Look for #EXTINF line
            if (line.startsWith("#EXTINF:-1")) {
                val name = extractAttribute(line, "tvg-name") 
                    ?: extractChannelName(line)
                val logo = extractAttribute(line, "tvg-logo") ?: ""
                val category = extractAttribute(line, "group-title") ?: "General"

                // Next line should be the stream URL
                if (i + 1 < lines.size) {
                    val url = lines[i + 1].trim()
                    if (url.isNotEmpty() && !url.startsWith("#")) {
                        channels.add(
                            Channel(
                                name = name,
                                streamUrl = url,
                                logo = logo,
                                category = category
                            )
                        )
                    }
                    i++
                }
            }
            i++
        }

        return channels
    }

    private fun extractAttribute(line: String, attrName: String): String? {
        val pattern = """$attrName="([^"]*)"""".toRegex()
        return pattern.find(line)?.groupValues?.get(1)
    }

    private fun extractChannelName(line: String): String {
        // Extract name after last comma
        val lastComma = line.lastIndexOf(",")
        return if (lastComma != -1) {
            line.substring(lastComma + 1).trim()
        } else {
            "Unknown Channel"
        }
    }
}

// Usage in your Activity/Fragment:
class ChannelActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        lifecycleScope.launch {
            val panelClient = MITVPanelClient()
            val channels = panelClient.fetchChannelsFromM3U(
                username = "user1",
                password = "pass123"
            )

            // Now use these channels in your RecyclerView, ExoPlayer, etc.
            displayChannels(channels)
        }
    }

    private fun displayChannels(channels: List<MITVPanelClient.Channel>) {
        // Bind to your UI
        channels.forEach { channel ->
            Log.d("MITV", "${channel.name} -> ${channel.streamUrl}")
        }
    }
}
