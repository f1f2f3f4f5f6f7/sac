import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { UserLogin, UserWithToken } from '../models/user.model';
import { BehaviorSubject, ignoreElements, map, Observable, tap } from 'rxjs';
import { Router } from '@angular/router';

const url = 'https://2z4cjldp-8000.use2.devtunnels.ms/api/accounts';
const USER_LOCAL_STORAGE_KEY = 'accessToken';

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

  login(userLogin: UserLogin): Observable<never> {
    return this._httpClient.post<any>(`${url}/login/`, userLogin).pipe(
      tap((response) => {
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
    console.log(user);
    this.user.next(user);
  }

  private loadUserFromLocalStorage(): void {
    const userFromLocal = localStorage.getItem(USER_LOCAL_STORAGE_KEY);

    userFromLocal && this.userLogged({ token: userFromLocal } as UserWithToken);
  }

  redirectTo(): void {
    this.router.navigateByUrl('/');
  }
}
