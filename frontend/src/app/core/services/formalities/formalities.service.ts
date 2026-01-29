import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { IInventaryWriteOff } from '../../models/inventary.model';
import { catchError, throwError } from 'rxjs';

const url = 'http://localhost:8000';

@Injectable({
  providedIn: 'root',
})
export class FormalitiesService {
  private _httpClient = inject(HttpClient);

  writeOff(items: IInventaryWriteOff[]) {
    const endpoint = `${url}/api/movimientos/solicitud_baja/`;

    return this._httpClient.post(endpoint, { items }, {responseType: 'blob'})
  }
}
