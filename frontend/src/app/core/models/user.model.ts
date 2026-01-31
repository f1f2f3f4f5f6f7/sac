import {RoleType } from "./role.enum"

export interface User {
    id: number,
    codigo: string,
    nombre: string,
    email: string,
    password: string,
    rol: RoleType,
    escuela: number,
    activo: boolean,
}

export type UserLogin = Omit<User, 'id' | 'nombre' | 'nombre' | 'email' | 'rol' | 'escuela' | 'activo'>

export type UserWithToken = Omit<User, 'password'> & { token: string }

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


  export interface UpdateUserRequest {
    codigo: string;
    email?: string;
    password?: string;
  }
  
  export interface UpdateUserResponse {
    success: boolean;
    message: string;
    user: {
      id: number;
      codigo: string;
      nombre: string;
      email: string;
      rol: string;
    };
  }

