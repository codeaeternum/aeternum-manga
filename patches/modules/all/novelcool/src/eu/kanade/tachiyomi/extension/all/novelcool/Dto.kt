package eu.kanade.tachiyomi.extension.all.novelcool

import eu.kanade.tachiyomi.source.model.Page
import eu.kanade.tachiyomi.source.model.SChapter
import eu.kanade.tachiyomi.source.model.SManga
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull

@Serializable
class BrowsePayload(
    private val appId: String,
    private val secret: String,
    private val lang: String,
    @SerialName("lc_type") private val lcType: String,
    private val page: String,
    @SerialName("page_size") private val pageSize: String,
    private val keyword: String? = null,
)

@Serializable
class BookPayload(
    private val appId: String,
    private val secret: String,
    private val lang: String,
    @SerialName("book_id") private val bookId: String,
)

@Serializable
class ChapterPayload(
    private val appId: String,
    private val secret: String,
    private val lang: String,
    @SerialName("chapter_id") private val chapterId: String,
)

@Serializable
class MangaListResponse(
    val list: List<MangaDto> = emptyList(),
)

@Serializable
class MangaDto(
    @SerialName("book_id") private val bookId: String,
    @SerialName("visit_path") private val visitPath: String,
    private val name: String,
    private val cover: String? = null,
) {
    fun toSManga() = SManga.create().apply {
        // The site urls need the slug and the API needs the id, so keep both.
        url = "$bookId/$visitPath"
        title = name
        thumbnail_url = cover
    }
}

@Serializable
class BookInfoResponse(
    val info: BookInfoDto,
)

@Serializable
class BookInfoDto(
    @SerialName("book_id") private val bookId: String,
    @SerialName("visit_path") private val visitPath: String,
    private val name: String,
    private val cover: String? = null,
    private val author: String? = null,
    private val artist: String? = null,
    private val intro: String? = null,
    private val completed: String? = null,
    @SerialName("category_list") private val categoryList: List<String> = emptyList(),
) {
    fun toSManga() = SManga.create().apply {
        url = "$bookId/$visitPath"
        title = name
        thumbnail_url = cover
        author = this@BookInfoDto.author?.trim()?.ifEmpty { null }
        artist = this@BookInfoDto.artist?.trim()?.ifEmpty { null }
        description = intro?.trim()
        genre = categoryList.joinToString()
        status = if (completed.equals("YES", ignoreCase = true)) SManga.COMPLETED else SManga.ONGOING
    }
}

@Serializable
class ChapterListResponse(
    val list: List<ChapterDto> = emptyList(),
)

@Serializable
class ChapterDto(
    private val id: String,
    private val title: String,
    private val type: Int = 1,
    @SerialName("order_id") private val orderId: String? = null,
    @SerialName("last_modify") private val lastModify: String? = null,
    @SerialName("is_locked") private val locked: JsonElement? = null,
) {
    // type 0 chapters are plain-text novel content; the API serves no pic_list for them
    val isReadable: Boolean get() = type != 0 && !isLocked

    private val isLocked: Boolean
        get() = (locked as? JsonPrimitive)?.let {
            if (it.isString) it.contentOrNull.equals("true", true) || it.contentOrNull == "1" else it.booleanOrNull == true
        } ?: false

    fun toSChapter() = SChapter.create().apply {
        url = id
        name = title
        chapter_number = orderId?.toFloatOrNull() ?: -1f
        date_upload = lastModify?.toLongOrNull()?.times(1000) ?: 0L
    }
}

@Serializable
class ChapterInfoResponse(
    val info: ChapterInfoDto,
)

@Serializable
class ChapterInfoDto(
    @SerialName("book_id") val bookId: String? = null,
    @SerialName("pic_list") private val picList: List<PageDto>? = null,
) {
    fun toPageList(): List<Page> = picList.orEmpty()
        .sortedBy { it.orderId }
        .mapIndexed { index, page -> Page(index, imageUrl = page.picPath) }
}

@Serializable
class PageDto(
    @SerialName("pic_path") val picPath: String,
    @SerialName("order_id") val orderId: Int = 0,
)
