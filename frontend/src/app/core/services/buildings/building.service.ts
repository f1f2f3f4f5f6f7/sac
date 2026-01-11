import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { BehaviorSubject, Observable, catchError, tap, throwError } from 'rxjs';

const url = 'http://localhost:8000';

@Injectable({
  providedIn: 'root',
})
export class BuildingService {
  private _httpClient = inject(HttpClient);
  private _buildings = new BehaviorSubject<any[]>([]);

  get buildings$(): Observable<any> {
    return this._buildings.asObservable();
  }

  set buildings(items: any[]) {
    this._buildings.next(items);
  }

  getBuildings(): any {
    return this._httpClient.get(`${url}/api/busquedaGeneral/listar-edificios/`).pipe(
      tap((response: any) => {
        this._buildings.next(response.edificios);
      }),
      catchError((error: any) => {
        this._buildings.next([]);
        return throwError(() => error);
      })
    );
  }
}
