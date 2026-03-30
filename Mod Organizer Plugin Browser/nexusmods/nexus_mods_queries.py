"""
Library of GraphQL queries for the Nexus Mods API.
"""

# Fetch MO2 Extensions (Plugins/Themes)
GET_MO2_EXTENSIONS = """
query GetMO2Extensions($count: Int, $facets: ModsFacet, $filter: ModsFilter, $offset: Int, $sort: [ModsSort!]) {
  mods(count: $count, facets: $facets, filter: $filter, offset: $offset, sort: $sort) {
    nodes {
      adultContent
      createdAt
      downloads
      endorsements
      fileSize
      modCategory {
        categoryId
        name
      }
      modId
      name
      status
      summary
      thumbnailUrl
      thumbnailBlurredUrl
      uid
      updatedAt
      uploader {
        avatar
        memberId
        name
      }
      viewerDownloaded
      viewerEndorsed
      viewerTracked
      viewerUpdateAvailable
      viewerIsBlocked
    }
    totalCount
    nodesCount
    facets {
      count
      facet
      value
    }
  }
}
"""

# Fetch files for a specific mod
GET_MOD_FILES = """
query getMO2PluginFiles($modId: ID!, $gameId: ID!) {
  modFiles(modId: $modId, gameId: $gameId) {
    category
    changelogText
    date
    description
    fileId
    id
    groupId
    name
    primary
    sizeInBytes
    version
    totalDownloads
    uid
    uniqueDownloads
    uri
  }
}
"""

GET_MODS_BY_UID = """
query getMO2PluginsByUid(
  $uids: [ID!]!,
  $offset: Int,
  $count: Int
) {
  modsByUid(
    uids: $uids,
    offset: $offset,
    count: $count
  ) {
    nodes {
      adultContent
      createdAt
      downloads
      endorsements
      fileSize
      modCategory {
        categoryId
        name
      }
      modId
      name
      status
      summary
      thumbnailUrl
      thumbnailBlurredUrl
      uid
      updatedAt
      uploader {
        avatar
        memberId
        name
      }
      viewerDownloaded
      viewerEndorsed
      viewerTracked
      viewerUpdateAvailable
      viewerIsBlocked
    }
    totalCount
    nodesCount
    facets {
      count
      facet
      value
    }
  }
}

"""