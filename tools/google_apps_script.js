/**
 * QYRON'27 — Google Drive Automatic Upload Webhook
 * 
 * HOW TO SET UP (Takes ~2 minutes):
 * 1. Go to https://script.google.com/
 * 2. Click "New project"
 * 3. Replace all code in Code.gs with this entire script and click Save (Ctrl+S).
 * 4. Click "Deploy" (top right button) -> "New deployment".
 * 5. Click the gear icon next to "Select type" and choose "Web app".
 * 6. Set:
 *    - Description: "QYRON 27 Uploads"
 *    - Execute as: "Me" (your Google account)
 *    - Who has access: "Anyone"   <-- (MUST be set to Anyone)
 * 7. Click "Deploy", click "Authorize access", choose your Google account, 
 *    click "Advanced" -> "Go to Untitled project (unsafe)" -> "Allow".
 * 8. Copy the "Web app URL" (starts with https://script.google.com/macros/s/.../exec).
 * 9. Paste it into your .env:
 *    GOOGLE_DRIVE_WEBHOOK_URL=https://script.google.com/macros/s/.../exec
 * 
 * OPTIONAL: To save files in a specific Google Drive folder instead of root:
 * 1. Open Google Drive, create/open a folder (e.g. "QYRON 27 Submissions").
 * 2. Copy the folder ID from the browser address bar (the string after /folders/...).
 * 3. Add to your .env:
 *    GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here
 */

function doPost(e) {
  try {
    var rawData = e.postData.contents;
    var data = JSON.parse(rawData);
    
    var filename = data.filename || "QYRON27_Submission.pptx";
    var mimeType = data.mimeType || "application/vnd.openxmlformats-officedocument.presentationml.presentation";
    var b64Data = data.base64;
    
    if (!b64Data) {
      return respondJson({ success: false, error: "Missing base64 data" });
    }
    
    var decoded = Utilities.base64Decode(b64Data);
    var blob = Utilities.newBlob(decoded, mimeType, filename);
    
    var folder;
    if (data.folderId && data.folderId.trim() !== "") {
      try {
        folder = DriveApp.getFolderById(data.folderId.trim());
      } catch (fErr) {
        folder = DriveApp.getRootFolder();
      }
    } else {
      folder = DriveApp.getRootFolder();
    }
    
    var file = folder.createFile(blob);
    // Allow anyone with the link to view the proposal
    try {
      file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
    } catch (shareErr) {
      // Continue even if organization policy blocks public link
    }
    
    var viewUrl = file.getUrl();
    var downloadUrl = file.getDownloadUrl();
    var fileId = file.getId();
    
    return respondJson({
      success: true,
      url: viewUrl,
      id: fileId,
      downloadUrl: downloadUrl,
      filename: filename
    });
  } catch (err) {
    return respondJson({
      success: false,
      error: err.toString()
    });
  }
}

function doGet(e) {
  return respondJson({
    status: "active",
    service: "QYRON'27 Google Drive Webhook",
    message: "POST base64 encoded presentation files here to upload automatically to Google Drive."
  });
}

function respondJson(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
