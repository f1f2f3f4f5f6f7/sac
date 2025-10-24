import { Component, EventEmitter, Output } from '@angular/core';
import { Html5Qrcode } from 'html5-qrcode';
import { DialogModule } from 'primeng/dialog';
import { Button } from 'primeng/button';

@Component({
  selector: 'app-barcode-reader',
  imports: [DialogModule, Button],
  templateUrl: './barcode-reader.html',
  styleUrl: './barcode-reader.scss',
  standalone: true,
})
export class BarcodeReader {
  visible: boolean = false;
  @Output() dataSent = new EventEmitter<string>();
  constructor() {}

  showDialog() {
    this.visible = true;
    Html5Qrcode.getCameras()
      .then((devices) => {
        /**
         * devices would be an array of objects of type:
         * { id: "id", label: "label" }
         */
        if (devices && devices.length) {
          let cameraId = devices[0].id;
          const html5QrCode = new Html5Qrcode('reader');
          html5QrCode
            .start(
              cameraId,
              {
                fps: 10, // Optional, frame per seconds for qr code scanning
                qrbox: { width: 350, height: 150 }, // Optional, if you want bounded box UI
              },
              (decodedText) => {
                html5QrCode
                  .stop()
                  .then((ignore) => {
                    this.visible = false;
                    this.dataSent.emit(decodedText);
                  })
                  .catch((err) => {
                    // Stop failed, handle it.
                  });
              },
              (errorMessage) => {
                // parse error, ignore it.
              }
            )
            .catch((err) => {
              // Start failed, handle it.
            });
        }
      })
      .catch((err) => {
        // handle err
      });
  }
}
