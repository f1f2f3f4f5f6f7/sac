import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { BehaviorSubject, Observable, tap, catchError, throwError } from 'rxjs';
import { ISchool } from '../../models/school.model';

const url = 'http://localhost:8000';

@Injectable({
  providedIn: 'root',
})
export class SchoolsService {
  private _httpClient = inject(HttpClient);
  private _schools = new BehaviorSubject<any[]>([]);

  get schools$(): Observable<any> {
    return this._schools.asObservable();
  }

  set schools(items: any[]) {
    this._schools.next(items);
  }

  getSchools(): Observable<ISchool[]> {
    return this._httpClient.get(`${url}/api/busquedaGeneral/listar-escuelas/`).pipe(
      tap((response: any) => {
        this._schools.next(response.escuelas);
      }),
      catchError((error: any) => {
        return throwError(() => error);
      }),
    );
  }
}
