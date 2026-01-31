import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { IInventaryLoan, IInventaryWriteOff } from '../../models/inventary.model';
import { catchError, throwError } from 'rxjs';

const url = 'http://localhost:8000';

@Injectable({
  providedIn: 'root',
})
export class FormalitiesService {
  private _httpClient = inject(HttpClient);

  tramite(items: IInventaryWriteOff[] | IInventaryLoan, request: string) {
    const endpoint = `${url}/api/movimientos/${request}/`;

    return this._httpClient.post(endpoint, { items }, {responseType: 'blob'})
  }
}
