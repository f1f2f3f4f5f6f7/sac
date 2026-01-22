import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { UserLogin, UserWithToken } from '../models/user.model';
import { BehaviorSubject, ignoreElements, map, Observable, tap, take } from 'rxjs';
import { Router } from '@angular/router';
import { Role } from '../models/role.enum';

const url = 'http://localhost:8000/api/accounts';
const USER_LOCAL_STORAGE_KEY = 'accessToken';
const ROLE_LOCAL_STORAGE_KEY = 'role';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private user = new BehaviorSubject<UserWithToken | null>(null);
  user$ = this.user.asObservable();
  islogged$: Observable<Boolean> = this.user$.pipe(map(Boolean));

  constructor(private _httpClient: HttpClient, private router: Router) {
    this.loadUserFromLocalStorage();
  }

  set accessToken(token: string) {
    localStorage.setItem('accessToken', token);
  }

  get accessToken(): string {
    return localStorage.getItem('accessToken') ?? '';
  }

  set role(role: string) {
    localStorage.setItem('role', role);
  }

  get role(): string {
    return localStorage.getItem('role') ?? '';
  }

  login(userLogin: UserLogin): Observable<never> {
    return this._httpClient.post<any>(`${url}/login/`, userLogin).pipe(
      tap((response) => {
        this.role = response.user.rol;
        this.accessToken = response.token;
      }),
      tap((response) => {
        this.userLogged(response.user as UserWithToken);
      }),
      tap(() => {
        this.redirectTo();
      }),
      ignoreElements()
    );
  }

  userLogged(user: UserWithToken | null): void {
    this.user.next(user);
  }

  private loadUserFromLocalStorage(): void {
    const userFromLocal = localStorage.getItem(USER_LOCAL_STORAGE_KEY);

    userFromLocal && this.userLogged({ token: userFromLocal } as UserWithToken);
  }

  redirectTo(): void {
    this.user$
      .pipe(
        take(1),
        tap((user) => {
          if (user?.rol === 'director') {
            this.router.navigateByUrl('/director');
          } else {
            this.router.navigateByUrl('/profesor');
          }
        })
      )
      .subscribe();
  }

  logout(): Observable<any> {
    return this._httpClient.post<any>(`${url}/logout/`, {}).pipe(
      tap(() => {
        // Limpiar token del localStorage
        localStorage.removeItem(USER_LOCAL_STORAGE_KEY);
        localStorage.removeItem(ROLE_LOCAL_STORAGE_KEY);
        // Limpiar usuario del estado
        this.userLogged(null);
        // Redirigir al login
        this.router.navigateByUrl('/login');
      })
    );
  }
}
