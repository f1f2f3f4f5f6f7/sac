import { FileUpload, FileUploadHandlerEvent } from "primeng/fileupload";

export interface FILEEVENTUPLOAD {
  originalEvent: FileUploadHandlerEvent;
  fileForm: FileUpload;
}