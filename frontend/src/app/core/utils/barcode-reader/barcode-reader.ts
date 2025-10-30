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
    Html5Qrcode.getCameras().then((devices) => {
      if (devices && devices.length) {
        const html5QrCode = new Html5Qrcode('reader');
        const qrCodeSuccessCallback = (decodedText: any, decodedResult: any) => {
          html5QrCode.stop().then(() => {
            this.visible = false;
            this.dataSent.emit(decodedText);
          });
        };
        const qrCodeErrorCallback = (error: any) => {};
        const config = { fps: 10, qrbox: { width: 250, height: 150 } };
        html5QrCode.start(
          { facingMode: 'environment' },
          config,
          qrCodeSuccessCallback,
          qrCodeErrorCallback
        );
      }
    });
  }
}
