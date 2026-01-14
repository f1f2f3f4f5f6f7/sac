import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { BehaviorSubject, Observable, catchError, tap, throwError } from 'rxjs';

const url = 'http://localhost:8000/api/accounts';

export interface UserFromBackend {
  id: number;
  codigo: string;
  nombre: string;
  email: string;
  rol: string;
  activo: boolean;
  escuela: {
    id: number;
    nombre: string;
  } | null;
}

export interface UsersListResponse {
  success: boolean;
  users: UserFromBackend[];
  total: number;
}

export interface RegisterUserRequest {
    codigo: string;
    nombre: string;
    email: string;
    password: string;
    rol: string;
    escuela_id: number;
  }
  
  export interface RegisterUserResponse {
    success: boolean;
    user: {
      id: number;
      codigo: string;
      nombre: string;
      email: string;
      rol: string;
    };
  }

  export interface DeleteUserRequest {
    codigo: string;
  }
  
  export interface DeleteUserResponse {
    success: boolean;
    message: string;
  }


@Injectable({
  providedIn: 'root',
})
export class UsersService {
  private _httpClient = inject(HttpClient);
  private _users = new BehaviorSubject<UserFromBackend[]>([]);

  get users$(): Observable<UserFromBackend[]> {
    return this._users.asObservable();
  }

  set users(items: UserFromBackend[]) {
    this._users.next(items);
  }

  getUsers(): Observable<UsersListResponse> {
    return this._httpClient.get<UsersListResponse>(`${url}/users/`).pipe(
      tap((response: UsersListResponse) => {
        if (response.success) {
          this._users.next(response.users);
        }
      }),
      catchError((error: any) => {
        this._users.next([]);
        return throwError(() => error);
      })
    );
  }

  registerUser(userData: RegisterUserRequest): Observable<RegisterUserResponse> {
    return this._httpClient.post<RegisterUserResponse>(`${url}/register/`, userData).pipe(
      catchError((error: any) => {
        return throwError(() => error);
      })
    );
  }


  deleteUser(codigo: string): Observable<DeleteUserResponse> {
    return this._httpClient.post<DeleteUserResponse>(`${url}/delete/`, { codigo }).pipe(
      catchError((error: any) => {
        return throwError(() => error);
      })
    );
  }
}