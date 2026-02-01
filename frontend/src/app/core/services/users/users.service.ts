import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { BehaviorSubject, Observable, catchError, tap, throwError } from 'rxjs';
import { DeleteUserResponse, RegisterUserRequest, RegisterUserResponse, UpdateUserRequest, UpdateUserResponse, UserFromBackend, UsersListResponse } from '../../models/user.model';

const url = 'http://localhost:8000/api/accounts';
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

  updateUser(userData: UpdateUserRequest): Observable<UpdateUserResponse> {
    return this._httpClient.post<UpdateUserResponse>(`${url}/update/`, userData).pipe(
      catchError((error: any) => {
        return throwError(() => error);
      })
    );
  }
}